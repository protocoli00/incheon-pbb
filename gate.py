import streamlit as st
import requests
import pandas as pd
from urllib.parse import unquote

st.title("🚨 에러 확인 모드")

# 1. 키 입력
api_key_input = st.text_input("API 키를 입력하세요", type="password")
real_key = unquote(api_key_input) if api_key_input else ""

# 2. 테스트 시작 버튼
if st.button("서버 연결 테스트 시작"):
    if not real_key:
        st.error("키를 입력해주세요!")
    else:
        st.info("인천공항 서버에 신호를 보내는 중...")
        
        # 테스트용 URL (T1 출발편 조회)
        url = "http://apis.data.go.kr/B551177/StatusOfPassengerFlightsOdp/getPassengerDeparturesOdp"
        params = {
            "serviceKey": real_key,
            "type": "json",
            "terminalId": "P01",
            "numOfRows": "10",
            "pageNo": "1"
        }
        
        try:
            response = requests.get(url, params=params)
            
            # 결과 화면에 출력
            st.write("--- 서버 응답 내용 ---")
            st.code(response.text) # 여기에 에러 메시지가 뜹니다
            
            # 에러 분석
            if "SERVICE_KEY_IS_NOT_REGISTERED_ERROR" in response.text:
                st.error("🔴 [원인] 키 등록 대기중")
                st.warning("공공데이터포털에서 키를 발급받은 지 1시간이 안 지났습니다. 서버가 아직 키를 인식 못하고 있어요. 잠시 후 다시 시도하세요.")
            elif "SERVICE_ACCESS_DENIED_ERROR" in response.text:
                 st.error("🔴 [원인] 신청되지 않은 API")
                 st.warning("활용 신청이 제대로 안 되었거나, '상세 조회' 서비스가 아닌 다른 API를 신청하신 것 같습니다.")
            elif "LIMITED_NUMBER_OF_SERVICE_REQUESTS_EXCEEDS_ERROR" in response.text:
                 st.error("🔴 [원인] 트래픽 초과")
            elif "response" in response.text and "body" in response.text:
                st.success("🟢 [성공] 연결 성공! 데이터가 정상적으로 오고 있습니다.")
                st.write("이제 원래 코드로 되돌리셔도 됩니다.")
            else:
                st.error("🔴 [원인] 기타 에러 (위의 영어 메시지를 확인하세요)")
                
        except Exception as e:
            st.error(f"프로그램 에러: {e}")
