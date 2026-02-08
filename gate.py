import streamlit as st
import requests
from urllib.parse import unquote

st.title("🕵️‍♀️ 내 API 찾기 테스트")

# 1. 키 입력
api_key_input = st.text_input("API 인증키를 입력하세요 (Decoding/Encoding 무관)", type="password")
real_key = unquote(api_key_input) if api_key_input else ""

st.markdown("---")
st.write("아래 두 버튼을 차례대로 눌러보세요.")

# ==========================================
# 테스트 1: 상세 조회 서비스 (Odp 버전)
# ==========================================
if st.button("테스트 1: 상세 조회 (Odp 버전)"):
    if not real_key:
        st.error("키를 먼저 입력하세요!")
    else:
        # Odp가 붙은 주소
        url = "http://apis.data.go.kr/B551177/StatusOfPassengerFlightsOdp/getPassengerDeparturesOdp"
        params = {"serviceKey": real_key, "type": "json", "terminalId": "P01", "numOfRows": "5", "pageNo": "1"}
        
        try:
            response = requests.get(url, params=params)
            st.write(f"응답 코드: {response.status_code}")
            
            if "response" in response.text and "body" in response.text:
                st.success("✅ 성공! 선생님은 [상세 조회 서비스(Odp)]를 신청하셨습니다.")
                st.balloons()
            elif "Forbidden" in response.text or "SERVICE_ACCESS_DENIED" in response.text:
                st.error("❌ 실패 (Forbidden). 이 API가 아닙니다.")
            else:
                st.warning(f"⚠️ 기타 응답: {response.text[:100]}")
        except Exception as e:
            st.error(f"에러 발생: {e}")

# ==========================================
# 테스트 2: 일반 조회 서비스 (기본 버전)
# ==========================================
if st.button("테스트 2: 일반 조회 (기본 버전)"):
    if not real_key:
        st.error("키를 먼저 입력하세요!")
    else:
        # Odp가 없는 주소
        url = "http://apis.data.go.kr/B551177/StatusOfPassengerFlights/getPassengerDepartures"
        params = {"serviceKey": real_key, "type": "json", "terminalId": "P01", "numOfRows": "5", "pageNo": "1"}
        
        try:
            response = requests.get(url, params=params)
            st.write(f"응답 코드: {response.status_code}")
            
            if "response" in response.text and "body" in response.text:
                st.success("✅ 성공! 선생님은 [일반 조회 서비스]를 신청하셨습니다.")
                st.info("이 버전은 '탑승마감' 같은 상세 정보가 없을 수도 있습니다.")
            elif "Forbidden" in response.text or "SERVICE_ACCESS_DENIED" in response.text:
                st.error("❌ 실패 (Forbidden). 이 API도 아닙니다.")
            else:
                st.warning(f"⚠️ 기타 응답: {response.text[:100]}")
        except Exception as e:
            st.error(f"에러 발생: {e}")
