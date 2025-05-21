import streamlit as st
import pandas as pd
from io import BytesIO

st.set_page_config(page_title="문제 검수 도구", layout="wide")

# 사이드바 메뉴
menu = st.sidebar.radio("페이지 선택", ["📤 엑셀 업로드", "🔍 문제 검수 및 다운로드"])

# 세션 상태 초기화
if 'df' not in st.session_state:
    st.session_state.df = None
if 'current_index' not in st.session_state:
    st.session_state.current_index = 0

# 1️⃣ 엑셀 업로드 페이지
if menu == "📤 엑셀 업로드":
    st.title("📤 엑셀 파일 업로드")
    uploaded_file = st.file_uploader("검수할 엑셀 파일 업로드 (.xlsx)", type=['xlsx'])

    if uploaded_file is not None:
        df = pd.read_excel(uploaded_file)

        # 'status' 열 없으면 추가
        if 'status' not in df.columns:
            df['status'] = ""

        st.session_state.df = df
        st.session_state.current_index = df[df['status'] == ""].index[0] if not df[df['status'] == ""].empty else 0
        st.success("✅ 파일 업로드 완료. 좌측 메뉴에서 문제 검수 페이지로 이동하세요.")

# 2️⃣ 문제 검수 및 다운로드 페이지
elif menu == "🔍 문제 검수 및 다운로드":
    df = st.session_state.df
    if df is None:
        st.warning("⚠️ 먼저 '엑셀 업로드' 페이지에서 파일을 업로드해주세요.")
    else:
        df_todo = df[df['status'] == ""]
        index = st.session_state.current_index
        row = df.iloc[index]

        # 상단 이동 & 다운로드
        col_top1, col_top2 = st.columns([3, 1])
        with col_top1:
            with st.form("move_form", clear_on_submit=True):
                input_number = st.text_input("🔍 문제 번호 이동 (1부터 시작)",placeholder="번호 입력 > 예시)30" label_visibility="collapsed",key="move_number_input")
                submitted = st.form_submit_button("이동")
                if submitted and input_number:
                    target = int(input_number) - 1
                    if 0 <= target < len(df):
                        st.session_state.current_index = target
                        st.rerun()
                    else:
                        st.warning("유효한 문제 번호 범위를 입력하세요.")

        with col_top2:
            output_all = BytesIO()
            with pd.ExcelWriter(output_all, engine='xlsxwriter') as writer:
                df.to_excel(writer, index=False, sheet_name='전체문제')
            st.download_button("📥 전체 문제 다운로드", output_all.getvalue(), "output_check.xlsx",
                               mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')

        # 본문 영역: 왼쪽 검수 화면 / 오른쪽 문제 리스트
        col_left, col_right = st.columns([4, 1.5])

        # 왼쪽: 현재 문제 검수
        with col_left:
            st.subheader(f"문제 {index + 1} / {len(df)}")
            st.text(f"과목: {row['subject']} / 장: {row['chapter']} / Q_IDX: {row['q_idx']}")
            st.markdown(f"**문제:** {row['question']}")
            st.markdown(f"**보기:** {row['content']}")
            st.markdown(f"- ① {row['ex1']}\n- ② {row['ex2']}\n- ③ {row['ex3']}\n- ④ {row['ex4']}")
            st.markdown(f"**해설:** {row['solve_gpt']}")
            st.markdown(f"**주제:** {row['관련 주제']}")
            st.markdown(f"**스크립트:** {row['관련 주제 스크립트']}")

            col_nav1, col_nav2, _ = st.columns(3)
            with col_nav1:
                if st.button("⬅️ 이전", use_container_width=True) and index > 0:
                    st.session_state.current_index -= 1
                    st.rerun()
            with col_nav2:
                if st.button("➡️ 다음", use_container_width=True) and index < len(df) - 1:
                    st.session_state.current_index += 1
                    st.rerun()

            col_btn1, col_btn2 = st.columns(2)
            with col_btn1:
                if st.button("✅ 검수 완료", use_container_width=True):
                    df.at[index, 'status'] = '검수 완료'
                    st.success("검수 완료로 처리됨.")
                    df_todo = df[df['status'] == '']
                    next_index = df_todo.index[0] if not df_todo.empty else min(index + 1, len(df) - 1)
                    st.session_state.current_index = next_index
                    st.rerun()
            with col_btn2:
                if st.button("⏸ 보류", use_container_width=True):
                    df.at[index, 'status'] = '보류'
                    st.warning("보류로 처리됨.")
                    df_todo = df[df['status'] == '']
                    next_index = df_todo.index[0] if not df_todo.empty else min(index + 1, len(df) - 1)
                    st.session_state.current_index = next_index
                    st.rerun()

        # 오른쪽: 전체 문제 리스트
        
        with col_right:
            st.markdown("### 🗂 문제 리스트 (고정 높이 스크롤 박스)")
        
            list_html = "<div style='height: 700px; overflow-y: auto;'>"
            for i in df.index:
                r = df.loc[i]
                status = r['status'] if r['status'] else '미검수'
                topic = r['관련 주제'] if pd.notna(r['관련 주제']) else '(주제 없음)'
                list_html += f"<p>문제 {i + 1} / Q_IDX: {r['q_idx']} / 주제:{topic} <b>[{status}]</b></p>"
            list_html += "</div>"
        
            st.markdown(list_html, unsafe_allow_html=True)
