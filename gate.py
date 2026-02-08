import streamlit as st
import requests
import pandas as pd
from urllib.parse import unquote

# ==========================================
# 1. 화면 설정
# ==========================================
st.set_page_config(page_title="PBB 현황판(전체운항)", page_icon="🛫")
st.title("🛫 PBB 출발 현황 (All Flight)")
st.caption("전체 운항 현황(출발) API 전용 버전")

# ==========================================
# 2. 설정 메뉴 (사이드바)
# ==========================================
with st.sidebar:
    st.header("설정")
    # 키 입력 (비밀번호처럼 가리기)
    api_key_input = st.text_input("인증키를 입력하세요", type="password")
    
    st.subheader("게이트 선택")
    # 게이트 입력 (기본값 예시)
    gate_input = st.text_input("게이트 번호 (쉼표로 구분)", value="10, 105, 230")
    
    if st.button("새로고침"):
        st.rerun()

# ==========================================
# 3. 데이터 가져오기 (전체 운항 API)
# ==========================================
def get_flight_data(key_input, gate_input_str):
    if not key_input:
        return pd.DataFrame()

    # 1. 키 보정 (자동으로 인코딩/디코딩 처리)
    real_key = unquote(key_input)
    
    # 2. 선생님이 찾으신 전체 운항(출발) API 주소
    url = "http://apis.data.go.kr/B551177/statusOfAllFltDeOdp/getStatusOfAllFltDeOdp"
    
    # 입력된 게이트 번호 정리 (공백 제거)
    target_gates = [g.strip() for g in gate_input_str.split(',') if g.strip()]
    all_flights = []

    # 터미널 전체 조회 (T1:P01, 탑승동:P02, T2:P03)
    terminals = {'T1': 'P01', '탑승동': 'P02', 'T2': 'P03'}
    
    for t_name, t_code in terminals.items():
        # 파라미터 설정
        params = {
            "serviceKey": real_key,
            "type": "json",
            "searchTerminalId": t_code, 
            "numOfRows": "100",
            "pageNo": "1"
        }
        
        try:
            # 5초 안에 응답 없으면 넘어가기
            response = requests.get(url, params=params, timeout=5)
            
            # JSON 데이터 파싱
            if response.status_code == 200:
                data = response.json()
                # 데이터가 있는지 확인
                if "response" in data and "body" in data["response"]:
                    items = data['response']['body']['items']
                    
                    # 아이템이 하나만 올 경우 리스트로 변환
                    if items and not isinstance(items, list): 
                        items = [items]
                    
                    if items:
                        for item in items:
                            # 게이트 번호 비교 (문자열로 변환하여 비교)
                            if str(item.get('gate')) in target_gates:
                                item['terminal_name'] = t_name
                                all_flights.append(item)
        except Exception as e:
            # 에러 발생 시 무시하고 다음 터미널 조회
            pass

    return pd.DataFrame(all_flights) if all_flights else pd.DataFrame()

# ==========================================
# 4. 화면 출력 (디자인)
# ==========================================
if not api_key_input:
    st.warning("👈 왼쪽 사이드바에 인증키를 입력해주세요.")
else:
    with st.spinner('전체 운항 데이터 조회 중...'):
        df = get_flight_data(api_key_input, gate_input)
    
    if df.empty:
        st.error("데이터가 없습니다.")
        st.info("가능성 1: 입력한 게이트에 출발편이 없음")
        st.info("가능성 2: 인증키 등록 대기중 (1시간 소요)")
        st.info("가능성 3: 인증키가 맞지 않음 (Encoding/Decoding)")
        
        # 직접 확인용 파란 링크 생성
        real_key = unquote(api_key_input)
        test_link = f"http://apis.data.go.kr/B551177/statusOfAllFltDeOdp/getStatusOfAllFltDeOdp?serviceKey={real_key}&type=json&searchTerminalId=P01&numOfRows=10&pageNo=1"
        st.markdown(f"[👉 클릭해서 외계어(데이터)가 나오는지 확인하기]({test_link})")
        
    else:
        st.success(f"총 {len(df)}개의 출발편을 찾았습니다.")
        
        # 시간순 정렬
        if 'scheduleDateTime' in df.columns:
            df = df.sort_values(by='scheduleDateTime')
        
        for index, row in df.iterrows():
            # 데이터 추출
            time_str = str(row.get('scheduleDateTime', ''))
            f_time = f"{time_str[8:10]}:{time_str[10:12]}" if len(time_str) >= 12 else "미정"
            
            remark = row.get('remark', '대기')
            if remark is None: remark = "대기" # 값이 없을 경우 대비
            
            flight_no = row.get('flightId', '-')
            airline = row.get('airline', '-')
            dest = row.get('airport', '-')
            gate = row.get('gate', '?')
            
            # 상태별 색상 설정
