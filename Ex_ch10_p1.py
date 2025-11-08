# 아래에 코드를 작성해주세요.
import pandas as pd
import streamlit as st

st.markdown("# 🌟 나의 소개 페이지")

st.markdown("## 👨‍💻 자기소개")
# st.markdown()을 사용하고 **로 묶어 굵게 표시합니다.
st.markdown("안녕하세요. 저는 **경영학과 25학번 신승한**이라고 합니다.")

# 섹션 사이에 구분선을 추가합니다.
st.divider()

st.markdown("## 🎧 좋아하는 것")
st.markdown("저는 **혼자만의 시간**을 보내는 것을 좋아합니다. 도서관에 앉아 이어폰으로 좋아하는 노래를 들으며 과제를 하거나, 아무도 없는 밤길을 홀로 걷는 등 나만의 **여유를 즐기는 순간**을 좋아합니다.")

# st.image(...) 코드를 삭제했습니다.

st.divider()

st.markdown("## 🎯 앞으로의 목표")
st.markdown("컴퓨팅 탐색 강의를 수강한 후 **코딩에 대한 이해도**를 높여, 작지만 구색을 갖춘 완전한 **저만의 프로그램**을 한번 만들어 보고 싶습니다.")
