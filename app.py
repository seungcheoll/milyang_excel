import streamlit as st
import pandas as pd
from io import BytesIO

st.set_page_config(page_title="문제 검수 도구", layout="wide")

# 페이지 선택
page = st.sidebar.radio("페이지 선택", ["📤 엑셀 업로드", "📝 문제 검수"])

# 상태 초기화
if 'uploaded_file' not in st.session_state:
    st.session_state.uploaded_file = None

# 페이지 1: 업로드
if page == "📤 엑셀 업로드":
    st.title("📤 엑셀 파일 업로드")
    uploaded_file = st.file_uploader("문제 데이터가 담긴 .xlsx 파일을 업로드하세요", type=["xlsx"])
    if uploaded_file:
        st.session_state.uploaded_file = uploaded_file
        st.success("파일이 업로드되었습니다. 📝 문제 검수 페이지로 이동하세요.")

# 페이지 2: 검수
elif page == "📝 문제 검수":
    if not st.session_state.uploaded_file:
        st.warning("왼쪽에서 엑셀 파일을 먼저 업로드하세요.")
    else:
        # 엑셀 원본 로드 (index 유지)
        df_all = pd.read_excel(st.session_state.uploaded_file, index_col=0)
        st.write("업로드된 데이터 컬럼 확인:", df_all.columns.tolist())
        if 'status' not in df_all.columns:
            df_all['status'] = ""

        # status가 비어 있는 문제만 필터링
        df_todo = df_all[df_all['status'].isna() | (df_all['status'] == "")]
        
        # 시작 위치 설정 (맨 처음 비어있는 index)
        if df_todo.empty:
            st.success("검수할 문제가 없습니다.")
            st.stop()
        else:
            if 'current_index' not in st.session_state:
                st.session_state.current_index = df_todo.index[0]

        current_index = st.session_state.current_index
        row = df_all.loc[current_index]

        # 문제 번호 검색 폼
        with st.form("move_form", clear_on_submit=True):
            input_number = st.text_input("", label_visibility="collapsed", placeholder="문제 번호 검색 > 예)30", key="move_number_input")
            submitted = st.form_submit_button("🔍 이동")
            if submitted and input_number:
                try:
                    target_index = int(input_number)
                    if target_index in df_todo.index:
                        st.session_state.current_index = target_index
                        st.rerun()
                    else:
                        st.warning("해당 문제는 이미 검수되었거나 존재하지 않습니다.")
                except ValueError:
                    st.error("숫자로 입력해 주세요.")

        # 레이아웃
        col_left, col_main, col_right = st.columns([1.5, 3, 1.5])

        # 중앙 문제 표시
        with col_main:
            st.subheader(f"문제 {current_index}")
            st.text(f"과목: {row['subject']} / 장: {row['chapter']} / Q_IDX: {row['q_idx']}")
            st.markdown(f"**문제:** {row['question']}")
            st.markdown(f"**보기:** {row['content']}")
            st.markdown(f"- ① {row['ex1']}\n- ② {row['ex2']}\n- ③ {row['ex3']}\n- ④ {row['ex4']}")
            st.markdown(f"**해설 (GPT):** {row['solve_gpt']}")
            st.markdown(f"**관련 주제:** {row['관련 주제']}")
            st.markdown(f"**스크립트:** {row['관련 주제 스크립트']}")

            # 이전/다음
            todo_indices = list(df_todo.index)
            current_pos = todo_indices.index(current_index)

            col_b1, col_b2, _ = st.columns(3)
            with col_b1:
                if current_pos > 0 and st.button("⬅️ 이전", use_container_width=True):
                    st.session_state.current_index = todo_indices[current_pos - 1]
                    st.rerun()
            with col_b2:
                if current_pos < len(todo_indices) - 1 and st.button("➡️ 다음", use_container_width=True):
                    st.session_state.current_index = todo_indices[current_pos + 1]
                    st.rerun()

            # 검수/보류
            col_a1, col_a2 = st.columns(2)
            with col_a1:
                if st.button("✅ 검수 완료", use_container_width=True):
                    df_all.at[current_index, 'status'] = "검수 완료"
                    if current_pos < len(todo_indices) - 1:
                        st.session_state.current_index = todo_indices[current_pos + 1]
                    st.rerun()
            with col_a2:
                if st.button("⏸ 보류", use_container_width=True):
                    df_all.at[current_index, 'status'] = "보류"
                    if current_pos < len(todo_indices) - 1:
                        st.session_state.current_index = todo_indices[current_pos + 1]
                    st.rerun()

        # 다운로드 버튼
        with col_right:
            st.markdown("### 📥 결과 다운로드")
            output = BytesIO()
            with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                df_all.to_excel(writer, index=True, sheet_name='전체문제')
            st.download_button(
                label="전체 문제 다운로드 (status 포함)",
                data=output.getvalue(),
                file_name="문제검수결과.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
