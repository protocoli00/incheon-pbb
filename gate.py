import streamlit as st

st.set_page_config(page_title="최종 링크 테스트", page_icon="🔗")
st.title("🔗 API 접속 주소 생성기")
st.info("아래에 키를 넣고 생성된 파란 링크를 클릭해보세요. 하얀 화면에 글자가 쫙 뜨면 성공입니다!")

# 1. 키 입력 (그냥 복사한 그대로 넣으세요)
api_key = st.text_input("공공데이터포털 인증키를 붙여넣으세요", value="")

if api_key:
    # 2. 테스트 링크 생성 (서버가 좋아하는 형태로 조립)
    
    # [시도 1] 상세 조회 (Odp) API + 입력한 키 그대로
    url_1 = f"http://apis.data.go.kr/B551177/StatusOfPassengerFlightsOdp/getPassengerDeparturesOdp?serviceKey={api_key}&type=json&terminalId=P01&numOfRows=5&pageNo=1"
    
    # [시도 2] 일반 조회 API + 입력한 키 그대로
    url_2 = f"http://apis.data.go.kr/B551177/StatusOfPassengerFlights/getPassengerDepartures?serviceKey={api_key}&type=json&terminalId=P01&numOfRows=5&pageNo=1"

    st.markdown("---")
    st.write("👇 **아래 링크를 하나씩 클릭해보세요.**")

    # 링크 1
    st.markdown(f"### [1번 링크: 상세 조회 (Odp) 테스트]({url_1})")
    st.caption("위 파란 글씨를 클릭하세요. 새 창에서 { ... } 데이터가 보이면 이게 정답입니다.")
    
    st.markdown("<br>", unsafe_allow_html=True) # 줄바꿈

    # 링크 2
    st.markdown(f"### [2번 링크: 일반 조회 테스트]({url_2})")
    st.caption("만약 1번이 에러나면 이걸 클릭해보세요.")

    st.markdown("---")
    st.warning("🚨 **클릭했을 때 화면에 뭐라고 뜨나요?**")
    st.text("성공 예시: {\"response\":{\"header\":{\"resultCode\":\"00\"} ...")
    st.text("실패 예시: <OpenAPI_ServiceResponse> ... SERVICE_KEY_IS_NOT_REGISTERED ...")
    st.text("실패 예시: 500 Internal Server Error (흰 화면)")
