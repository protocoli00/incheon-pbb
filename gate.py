import streamlit as st
import requests
from urllib.parse import unquote

st.set_page_config(page_title="API 진단 키트", page_icon="🩺")
st.title("🩺 API 연결 정밀 진단")
st.info("선생님의 키가 어떤 문을 열 수 있는지 4가지 방법으로 테스트합니다.")

# 1. 키 입력
api_key_input = st.text_input("공공데이터포털 API 인증키를 입력하세요 (Encoding/Decoding 상관없음)", type="password")

if st.button("🚀 맞는 접속 방법 찾기 (클릭)"):
    if not api_key_input:
        st.error("키를 입력해주세요!")
    else:
        # 테스트할 두 가지 API 주소 (상세 vs 일반)
        urls = {
            "A. [상세 조회 API] (StatusOfPassengerFlightsOdp)": "http://apis.data.go.kr/B551177/StatusOfPassengerFlightsOdp/getPassengerDeparturesOdp",
            "B. [일반 조회 API] (StatusOfPassengerFlights)": "http://apis.data.go.kr/B551177/StatusOfPassengerFlights/getPassengerDepartures"
        }
        
        # 키 처리 방식 (디코딩 후 재인코딩)
        # requests 라이브러리는 파라미터를 자동으로 인코딩하므로, 입력받은 키를 일단 디코딩해서 원본으로 만듦
        real_key = unquote(api_key_input)
        
        success_found = False

        for name, url in urls.items():
            st.write(f"--- 📡 {name} 테스트 중 ---")
            
            # 파라미터 설정
            params = {
                "serviceKey": real_key, # 여기서 자동으로 인코딩됨
                "type": "json",
                "terminalId": "P01", # T1
                "numOfRows": "5",
                "pageNo": "1"
            }
            
            try:
                # 요청 보내기
                response = requests.get(url, params=params, timeout=10)
                
                # 결과 분석
                if response.status_code == 200:
                    data = response.text
                    if "response" in data and "body" in data and "items" in data:
                        st.success(f"✅ **성공! 선생님은 [{name}]를 신청하셨군요!**")
                        st.json(response.json()['response']['body']['items'][0]) # 증거 데이터 보여줌
                        success_found = True
                        break # 성공했으니 멈춤
                    elif "SERVICE_KEY_IS_NOT_REGISTERED_ERROR" in data:
                        st.warning(f"⚠️ {name}: 키는 맞는데 아직 등록 대기중입니다 (1시간 뒤 재시도).")
                    elif "Forbidden" in data or "SERVICE_ACCESS_DENIED_ERROR" in data:
                        st.error(f"⛔ {name}: 이 API 권한이 없습니다. (신청 안 함)")
                    else:
                        st.warning(f"❓ {name}: 알 수 없는 응답 -> {data[:100]}")
                else:
                    st.error(f"❌ {name}: 서버 에러 (코드 {response.status_code})")
                    
            except Exception as e:
                st.error(f"통신 오류: {e}")

        if not success_found:
            st.markdown("---")
            st.error("😓 **모든 테스트 실패**")
            st.write("1. 공공데이터포털에서 **'활용신청'**이 승인되었는지 확인해주세요.")
            st.write("2. 신청하신 API 이름이 **'인천국제공항공사_여객기 운항 현황 상세 조회 서비스'**가 맞는지 확인해주세요.")
            st.write("3. 신청 직후라면 **1시간 뒤**에 다시 해보세요.")
