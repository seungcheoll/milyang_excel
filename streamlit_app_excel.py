import streamlit as st
import pandas as pd
from openai import OpenAI
from io import BytesIO
import matplotlib.pyplot as plt
import re

# 페이지 설정
st.set_page_config(page_title="엑셀 편집 + GPT 분석", layout="wide")
st.sidebar.title("📁 메뉴 선택")
menu = st.sidebar.radio("기능 선택", ["📂 엑셀 편집 페이지", "🤖 GPT 분석 페이지"])

# API 키 로드
api_key = st.secrets["general"]["OPEN_API_KEY"]
client = OpenAI(api_key=api_key)

# 공통 저장소
if "merged_df" not in st.session_state:
    st.session_state.merged_df = None

# 📂 엑셀 편집 페이지
if menu == "📂 엑셀 편집 페이지":
    st.title("📂 엑셀 파일 개별 편집")

    uploaded_files = st.file_uploader(
        "엑셀 파일을 하나 이상 업로드하세요",
        type=["xlsx", "xls"],
        accept_multiple_files=True
    )

    edited_dfs = {}

    if uploaded_files:
        for i, file in enumerate(uploaded_files):
            with st.expander(f"📄 {file.name} - 편집 옵션"):
                try:
                    df = pd.read_excel(file)
                    st.write("🗂️ 원본 데이터 미리보기")
                    st.dataframe(df, use_container_width=True)

                    cols_to_drop = st.multiselect(
                        f"[{file.name}] 삭제할 열 선택", df.columns.tolist(), key=f"cols_{i}"
                    )
                    if cols_to_drop:
                        df = df.drop(columns=cols_to_drop)

                    row_indices = st.multiselect(
                        f"[{file.name}] 삭제할 행 인덱스 선택", df.index.tolist(), key=f"rows_{i}"
                    )
                    if row_indices:
                        df = df.drop(index=row_indices)

                    edited_dfs[file.name] = df
                    st.dataframe(df, use_container_width=True)

                except Exception as e:
                    st.error(f"❌ {file.name} 처리 중 오류: {e}")

        if st.button("📎 최종 병합하기"):
            if edited_dfs:
                try:
                    merged_df = pd.concat(edited_dfs.values(), ignore_index=True)
                    st.session_state.merged_df = merged_df
                    st.success("✅ 병합 완료! GPT 페이지에서 분석 가능합니다.")
                    st.dataframe(merged_df, use_container_width=True)

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

# 🤖 GPT 분석 페이지
elif menu == "🤖 GPT 분석 페이지":
    st.title("🤖 GPT 기반 데이터 분석")

    if st.session_state.merged_df is not None:
        st.subheader("📊 병합된 데이터 미리보기")
        st.dataframe(st.session_state.merged_df, use_container_width=True)

        if st.button("🚀 GPT 자동 분석 실행 (데이터에 대한 간략한 설명 제공)"):
            try:
                df_csv = st.session_state.merged_df.to_csv(index=False)
                auto_prompt = f"""
다음은 사용자가 병합한 엑셀 데이터입니다. 이 데이터를 기반으로 주요 통계, 트렌드, 패턴을 자유롭게 분석해서 요약해 주세요.

[CSV 데이터]
{df_csv}
"""
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

        if "auto_response" in st.session_state:
            st.success("✅ GPT 자동 분석 결과")
            st.markdown(st.session_state.auto_response)

        st.markdown("---")
        st.markdown("## 💬 GPT 분석 질문")

        col1, col2 = st.columns(2)

        # 일반 질문
        with col1:
            st.markdown("### 📌 일반 질문")
            text_question = st.text_area("💬 질문을 입력하세요", placeholder="예: 주요 트렌드를 요약해주세요.", key="general_q")
            if st.button("💡 GPT에게 일반 질문 요청", key="general_btn"):
                try:
                    df_csv = st.session_state.merged_df.to_csv(index=False)
                    general_prompt = f"""
다음은 사용자가 업로드한 엑셀 데이터를 CSV 형태로 제공한 것입니다. 이 데이터를 분석해서 아래 일반 질문에 답변해주세요.

[CSV 데이터]
{df_csv}

[사용자 질문]
{text_question}
"""
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

        # 시각화 질문
        with col2:
            st.markdown("### 📊 시각화 관련 질문")
            viz_question = st.text_area("📈 질문을 입력하세요", placeholder="예: 제품별 판매량을 막대 그래프로 보여주세요.", key="viz_q")
            if st.button("📊 GPT에게 시각화 요청", key="viz_btn"):
                try:
                    df_csv = st.session_state.merged_df.to_csv(index=False)
                    viz_prompt = f"""
다음은 사용자가 업로드한 엑셀 데이터를 CSV 형태로 제공한 것입니다. 이 데이터를 분석해서 사용자 시각화 질문에 답변해주세요.

[코드와 같이 출력될 경우]
1. df는 이미 정의되어 있으므로, df를 새로 생성하지 말고 바로 사용
2. 코드를 제외한 모든 텍스트를 출력하지 않음
3. **matplotlib 사용 시 한글 폰트를 수동으로 설정 (koreanize-matplotlib 사용하지 마세요)**
4. 만약 텍스트가 출력되면 앞에 #을 붙여 출력

[CSV 데이터]
{df_csv}

[시각화 질문]
{viz_question}
"""
                    response = client.chat.completions.create(
                        model="gpt-4o",
                        messages=[
                            {"role": "system", "content": "당신은 데이터 분석 전문가입니다."},
                            {"role": "user", "content": viz_prompt}
                        ],
                        temperature=0.5
                    )
                    raw = response.choices[0].message.content
                    match = re.search(r"```(?:python)?\n(.*?)```", raw, re.DOTALL)
                    code = match.group(1).strip() if match else raw.strip()

                    # GPT 코드 저장
                    st.session_state.viz_code = code

                    # 실행 및 시각화 저장
                    df = st.session_state.merged_df.copy()
                    local_vars = {"df": df, "plt": plt, "pd": pd}
                    exec(code, {}, local_vars)

                    buf = BytesIO()
                    plt.savefig(buf, format="png", bbox_inches='tight')
                    buf.seek(0)
                    st.session_state.viz_image = buf

                except Exception as e:
                    st.session_state.viz_code = f"# ❌ GPT 호출 실패: {e}"
                    st.session_state.viz_image = None

            if "viz_code" in st.session_state:
                st.code(st.session_state.viz_code, language='python')
                if st.session_state.viz_image:
                    st.pyplot(plt)
                    st.download_button(
                        label="📸 그래프 PNG 다운로드",
                        data=st.session_state.viz_image,
                        file_name="graph.png",
                        mime="image/png"
                    )
    else:
        st.warning("먼저 '엑셀 편집 페이지'에서 병합된 데이터를 생성해주세요.")
