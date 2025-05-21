import streamlit as st
import pandas as pd
from io import BytesIO

st.set_page_config(page_title="문제 검수 도구", layout="wide")

# 사이드바로 페이지 선택
page = st.sidebar.radio("페이지 선택", ["📤 엑셀 업로드", "📝 문제 검수"])

# 파일 저장용 상태 초기화
if 'uploaded_file' not in st.session_state:
    st.session_state.uploaded_file = None

# 페이지 1: 엑셀 업로드
if page == "📤 엑셀 업로드":
    st.title("📤 엑셀 파일 업로드")
    uploaded_file = st.file_uploader("문제 데이터가 담긴 .xlsx 파일을 업로드하세요", type=["xlsx"])

    if uploaded_file:
        st.session_state.uploaded_file = uploaded_file
        st.success("파일이 업로드되었습니다. 상단 메뉴에서 📝 문제 검수 페이지로 이동하세요.")

# 페이지 2: 문제 검수
elif page == "📝 문제 검수":

    if not st.session_state.uploaded_file:
        st.warning("먼저 왼쪽 메뉴에서 📤 엑셀 파일을 업로드해주세요.")
    else:
        df = pd.read_excel(st.session_state.uploaded_file)

        if 'current_index' not in st.session_state:
            st.session_state.current_index = 0
        if '보류_리스트' not in st.session_state:
            st.session_state.보류_리스트 = []
        if '검수_리스트' not in st.session_state:
            st.session_state.검수_리스트 = []

        total_questions = len(df)

        # 문제 번호 이동
        with st.form("move_form", clear_on_submit=True):
            input_number = st.text_input("", label_visibility="collapsed",placeholder="문제 번호 검색 > 예)30",key="move_number_input")
            submitted = st.form_submit_button("🔍 이동")
            if submitted and input_number:
                try:
                    input_number_int = int(input_number)
                    if 1 <= input_number_int <= total_questions:
                        st.session_state.current_index = input_number_int - 1
                        st.rerun()
                    else:
                        st.warning(f"문제 번호는 1부터 {total_questions} 사이여야 합니다.")
                except ValueError:
                    st.error("숫자 형식으로 입력해 주세요.")

        index = st.session_state.current_index
        row = df.iloc[index]

        # 레이아웃: 왼쪽(검수), 가운데(문제), 오른쪽(보류)
        col_left, col_main, col_right = st.columns([1.5, 3, 1.5])

        # 중앙: 현재 문제 표시
        with col_main:
            st.subheader(f"문제 {index + 1} / {total_questions}")
            st.text(f"과목: {row['subject']} / 장: {row['chapter']} / Q_IDX: {row['q_idx']}")
            st.markdown(f"**문제:** {row['question']}")
            st.markdown(f"**보기:** {row['content']}")
            st.markdown(f"- ① {row['ex1']}\n- ② {row['ex2']}\n- ③ {row['ex3']}\n- ④ {row['ex4']}")
            st.markdown(f"**해설 (GPT):** {row['solve_gpt']}")
            st.markdown(f"**관련 주제:** {row['관련 주제']}")
            st.markdown(f"**스크립트:** {row['관련 주제 스크립트']}")

            # 이전/다음 버튼
            col_b1, col_b2, _ = st.columns(3)
            with col_b1:
                if st.button("⬅️ 이전", use_container_width=True) and index > 0:
                    st.session_state.current_index -= 1
                    st.rerun()
            with col_b2:
                if st.button("➡️ 다음", use_container_width=True) and index < total_questions - 1:
                    st.session_state.current_index += 1
                    st.rerun()

            # 검수/보류 버튼
            col_a1, col_a2 = st.columns(2)
            with col_a1:
                if st.button("✅ 검수 완료", use_container_width=True):
                    검수_항목 = {"번호": index + 1, "idx": row["q_idx"], "주제": row["관련 주제"]}
                    if 검수_항목 not in st.session_state.검수_리스트:
                        st.session_state.검수_리스트.append(검수_항목)
                    if index < total_questions - 1:
                        st.session_state.current_index += 1
                        st.rerun()
            with col_a2:
                if st.button("⏸ 보류", use_container_width=True):
                    보류_항목 = {"번호": index + 1, "idx": row["q_idx"], "주제": row["관련 주제"]}
                    if 보류_항목 not in st.session_state.보류_리스트:
                        st.session_state.보류_리스트.append(보류_항목)
                    if index < total_questions - 1:
                        st.session_state.current_index += 1
                        st.rerun()

        # 왼쪽: 검수 완료 목록
        with col_left:
            st.markdown("### ✅ 검수 완료 목록")
            if st.session_state.검수_리스트:
                for idx, item in enumerate(st.session_state.검수_리스트):
                    col1, col2 = st.columns([4, 1])
                    with col1:
                        st.markdown(f"- **문제 {item['번호']}번** / Q_IDX: {item['idx']} / 주제: {item['주제']}")
                    with col2:
                        if st.button("❌", key=f"delete_checked_{idx}"):
                            st.session_state.검수_리스트.pop(idx)
                            st.rerun()
                검수_번호들 = [item['번호'] for item in st.session_state.검수_리스트]
                검수_문제_df = df.iloc[[번호 - 1 for 번호 in 검수_번호들]]
                output1 = BytesIO()
                with pd.ExcelWriter(output1, engine='xlsxwriter') as writer:
                    검수_문제_df.to_excel(writer, index=False, sheet_name='검수완료')
                st.download_button("📥 검수 완료 다운로드", data=output1.getvalue(), file_name="검수완료.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
            else:
                st.info("검수 완료된 문제가 없습니다.")

        # 오른쪽: 보류 목록
        with col_right:
            st.markdown("### 📝 보류된 문제 목록")
            if st.session_state.보류_리스트:
                for idx, item in enumerate(st.session_state.보류_리스트):
                    col1, col2 = st.columns([4, 1])
                    with col1:
                        st.markdown(f"- **문제 {item['번호']}번** / Q_IDX: {item['idx']} / 주제: {item['주제']}")
                    with col2:
                        if st.button("❌", key=f"delete_hold_{idx}"):
                            st.session_state.보류_리스트.pop(idx)
                            st.rerun()
                보류_번호들 = [item['번호'] for item in st.session_state.보류_리스트]
                보류_문제_df = df.iloc[[번호 - 1 for 번호 in 보류_번호들]]
                output2 = BytesIO()
                with pd.ExcelWriter(output2, engine='xlsxwriter') as writer:
                    보류_문제_df.to_excel(writer, index=False, sheet_name='보류문제')
                st.download_button("📥 보류 문제 다운로드", data=output2.getvalue(), file_name="보류문제.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
            else:
                st.info("보류된 문제가 없습니다.")
