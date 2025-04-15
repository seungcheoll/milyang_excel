import streamlit as st
import pandas as pd
from openai import OpenAI
from io import BytesIO
import matplotlib.pyplot as plt
import re
import plotly.express as px
import ast

# Streamlit 웹앱 기본 설정
st.set_page_config(page_title="엑셀 편집 + GPT 분석", layout="wide")

# 사이드바 메뉴 구성
st.sidebar.title("📁 메뉴 선택")
menu = st.sidebar.radio("기능 선택", ["📂 엑셀 편집 페이지", "🤖 GPT 분석 페이지"])

# API 키 로드
api_key = st.secrets["general"]["OPEN_API_KEY"]
client = OpenAI(api_key=api_key)

# 세션 상태 변수 초기화 (병합된 데이터 저장용)
if "merged_df" not in st.session_state:
    st.session_state.merged_df = None

# === 안전 코드 실행 검사기 ===
# 사용자가 GPT로 받은 코드를 실행하기 전에 위험한 명령어가 포함됐는지 검사
class SafetyVisitor(ast.NodeVisitor):
    def __init__(self):
        self.safe = True  # 기본적으로 안전하다고 설정

    def visit_Import(self, node):
        # os, sys 등 위험한 모듈 사용 시 unsafe로 표시
        for alias in node.names:
            if alias.name in ("os", "sys", "subprocess", "shutil", "pickle", "socket"):
                self.safe = False

    def visit_ImportFrom(self, node):
        if node.module in ("os", "sys", "subprocess", "shutil", "pickle", "socket"):
            self.safe = False

    def visit_Call(self, node):
        # eval, exec 등 실행 명령 차단
        if isinstance(node.func, ast.Name) and node.func.id in ("eval", "exec", "open", "input", "compile", "__import__"):
            self.safe = False
        self.generic_visit(node)

    def visit_While(self, node):
        # 무한루프 차단
        if isinstance(node.test, ast.Constant) and node.test.value is True:
            self.safe = False
        self.generic_visit(node)

# 문자열 코드를 AST로 변환 후 위험 여부 확인
def is_safe_ast(code: str) -> bool:
    try:
        tree = ast.parse(code)
        visitor = SafetyVisitor()
        visitor.visit(tree)
        return visitor.safe
    except SyntaxError:
        return False

# === 📂 엑셀 편집 페이지 ===
if menu == "📂 엑셀 편집 페이지":
    st.title("📂 엑셀 파일 개별 편집")

    # 엑셀 파일 업로드 받기 (복수 가능)
    uploaded_files = st.file_uploader("엑셀 파일을 하나 이상 업로드하세요", type=["xlsx", "xls"], accept_multiple_files=True)

    edited_dfs = {}  # 각 파일별 편집된 데이터프레임 저장용 딕셔너리

    # 파일을 업로드한 경우
    if uploaded_files:
        for i, file in enumerate(uploaded_files):
            with st.expander(f"📄 {file.name} - 편집 옵션"):
                try:
                    # 파일을 데이터프레임으로 읽기
                    df = pd.read_excel(file)
                    st.write("🗂️ 원본 데이터 미리보기")
                    st.dataframe(df, use_container_width=True)

                    # 열 삭제 기능
                    cols_to_drop = st.multiselect(f"[{file.name}] 삭제할 열 선택", df.columns.tolist(), key=f"cols_{i}")
                    if cols_to_drop:
                        df = df.drop(columns=cols_to_drop)

                    # 행 삭제 기능
                    row_indices = st.multiselect(f"[{file.name}] 삭제할 행 인덱스 선택", df.index.tolist(), key=f"rows_{i}")
                    if row_indices:
                        df = df.drop(index=row_indices)

                    # 편집 완료된 데이터 저장
                    edited_dfs[file.name] = df
                    st.dataframe(df, use_container_width=True)

                except Exception as e:
                    st.error(f"❌ {file.name} 처리 중 오류: {e}")

        # 병합 버튼 누르면 모든 파일을 하나로 합치기
        if st.button("📎 최종 병합하기"):
            if edited_dfs:
                try:
                    merged_df = pd.concat(edited_dfs.values(), ignore_index=True)
                    st.session_state.merged_df = merged_df  # 세션에 저장
                    st.success("✅ 병합 완료! GPT 페이지에서 분석 가능합니다.")
                    st.dataframe(merged_df, use_container_width=True)

                    # 병합 파일 다운로드 기능
                    output = BytesIO()
                    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                        merged_df.to_excel(writer, index=False, sheet_name='병합데이터')
                    output.seek(0)

                    st.download_button(
                        label="📥 병합된 엑셀 다운로드",
                        data=output,
                        file_name="merged_result.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    )

                except Exception as e:
                    st.error(f"❌ 병합 실패: {e}")
            else:
                st.warning("편집된 데이터가 없습니다.")
    else:
        st.info("왼쪽에서 엑셀 파일을 업로드해주세요.")

# === 🤖 GPT 분석 페이지 ===
elif menu == "🤖 GPT 분석 페이지":
    st.title("🤖 GPT 기반 데이터 분석")

    if st.session_state.merged_df is not None:
        st.subheader("📊 병합된 데이터 미리보기")
        st.dataframe(st.session_state.merged_df, use_container_width=True)

        # GPT를 이용해 전체 데이터에 대한 간단한 분석 실행
        if st.button("🚀 GPT 자동 분석 실행 (데이터에 대한 간략한 설명 제공)"):
            try:
                df_csv = st.session_state.merged_df.to_csv(index=False)
                with open("template/auto_prompt.txt", "r", encoding="utf-8") as file:
                    auto_template = file.read()
                auto_prompt = auto_template.format(df_csv=df_csv)  # ✅ df_csv 삽입
                response = client.chat.completions.create(
                    model="gpt-4o",
                    messages=[
                        {"role": "system", "content": "당신은 데이터 분석 전문가입니다. 주어진 데이터의 인사이트를 추출해 주세요."},
                        {"role": "user", "content": auto_prompt}
                    ],
                    temperature=0.5
                )
                st.session_state.auto_response = response.choices[0].message.content
            except Exception as e:
                st.session_state.auto_response = f"❌ GPT 호출 실패: {e}"

        # GPT 분석 결과 출력
        if "auto_response" in st.session_state:
            st.success("✅ GPT 자동 분석 결과")
            st.markdown(st.session_state.auto_response)

        st.markdown("---")
        st.markdown("## 💬 GPT 분석 질문")

        col1, col2 = st.columns(2)

        # 📌 일반 질문: 분석 질문 입력창
        with col1:
            st.markdown("### 📌 일반 질문")
            text_question = st.text_area("💬 질문을 입력하세요", placeholder="예: 주요 트렌드를 요약해주세요.", key="general_q")
            if st.button("💡 GPT에게 일반 질문 요청", key="general_btn"):
                try:
                    df_csv = st.session_state.merged_df.to_csv(index=False)
                    with open("template/general_prompt.txt", "r", encoding="utf-8") as file:
                        general_template = file.read()
                    general_prompt = general_template.format(df_csv=df_csv, text_question=text_question)  # ✅ 질문 + CSV 삽입
                    response = client.chat.completions.create(
                        model="gpt-4o",
                        messages=[
                            {"role": "system", "content": "당신은 데이터 분석 전문가입니다."},
                            {"role": "user", "content": general_prompt}
                        ],
                        temperature=0.5
                    )
                    st.session_state.general_response = response.choices[0].message.content
                except Exception as e:
                    st.session_state.general_response = f"❌ GPT 호출 실패: {e}"

            if "general_response" in st.session_state:
                st.success("✅ GPT 일반 분석 결과")
                st.markdown(st.session_state.general_response)

        # 📊 시각화 질문: 그래프 생성 요청
        with col2:
            st.markdown("### 📊 시각화 관련 질문")
            viz_question = st.text_area("📈 질문을 입력하세요", placeholder="예: 제품별 판매량을 막대 그래프로 보여주세요.", key="viz_q")
            
            if st.button("📊 GPT에게 시각화 요청", key="viz_btn"):
                try:
                    df_csv = st.session_state.merged_df.to_csv(index=False)
                    with open("template/viz_prompt.txt", "r", encoding="utf-8") as file:
                        viz_template = file.read()
                    viz_prompt = viz_template.format(df_csv=df_csv, viz_question=viz_question)
                    response = client.chat.completions.create(
                        model="gpt-4o",
                        messages=[
                            {"role": "system", "content": "당신은 데이터 시각화 전문가이며, 반드시 plotly로만 코드를 작성합니다."},
                            {"role": "user", "content": viz_prompt}
                        ],
                        temperature=0.5
                    )

                    raw = response.choices[0].message.content
                    match = re.search(r"```(?:python)?\n(.*?)```", raw, re.DOTALL)
                    code = match.group(1).strip() if match else raw.strip()

                    st.session_state.viz_code = code

                    # GPT가 작성한 코드 실행 (안전성 검사 먼저)
                    df = st.session_state.merged_df.copy()
                    local_vars = {"df": df, "px": px, "pd": pd}

                    if is_safe_ast(code):
                        exec(code, {}, local_vars)
                        fig = None
                        for var in local_vars.values():
                            if hasattr(var, "to_plotly_json"):
                                fig = var
                                break
                        st.session_state.viz_figure = fig if fig else None
                        if not fig:
                            st.warning("✅ 실행은 되었지만 plotly 그래프가 탐지되지 않았습니다.")
                    else:
                        st.session_state.viz_code = "# ❌ 코드 실행 차단됨: 위험한 코드가 감지되었습니다."
                        st.session_state.viz_figure = None
                        st.warning("⚠️ GPT 코드에 위험한 명령이 포함되어 있어 실행을 차단했습니다.")

                except Exception as e:
                    st.session_state.viz_code = f"# ❌ GPT 호출 실패 또는 실행 에러: {e}"
                    st.session_state.viz_figure = None

            # 코드와 결과 그래프 표시
            if "viz_code" in st.session_state:
                st.code(st.session_state.viz_code, language='python')
                if st.session_state.viz_figure:
                    st.plotly_chart(st.session_state.viz_figure, use_container_width=True)
    else:
        st.warning("먼저 '엑셀 편집 페이지'에서 병합된 데이터를 생성해주세요.")
