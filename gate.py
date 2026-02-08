import streamlit as st
import requests
import pandas as pd
from urllib.parse import unquote

# ==========================================
# 1. 화면 설정
# ==========================================
st.set_page_config(page_title="PBB 현황판(전체운항)", page_icon="🛫")
st.title("🛫 PBB 출발 현황 (All Flight)")
st.caption("선생님의 키(전체 운항 현황)에 맞춘 전용 버전입니다.")

# ==========================================
# 2. 설정 메뉴
# ==========================================
with st.sidebar:
    st.header("설정")
    # 키 입력
    api_key_input = st.text_input("인증키를 입력하세요", type="password")
    
    st.subheader("게이트 선택")
    # 게이트 입력
    gate_input = st.text_input("게이트 번호 (쉼표로 구분)", value="10, 105, 230")
    
    if st.button("새로고침"):
        st.rerun()

# ==========================================
# 3. 데이터 가져오기 (전체 운항 현황 API 사용)
# ==========================================
def get_flight_data(key_input, gate_input_str):
    # 1. 키 보정 (자동으로 인코딩/디코딩 처리)
    real_key = unquote(key_input)
    
    # 2. 선생님이 찾으신 그 주소! (전체 운항 현황 - 출발)
    # 보통 오퍼레이션 이름은 getStatusOfAllFltDeOdp 입니다.
    url = "http://apis.data.go.kr/B551177/statusOfAllFltDeOdp/getStatusOfAllFltDeOdp"
    
    target_gates = [g.strip() for g in gate_input_str.split(',') if g.strip()]
    all_flights = []

    # 터미널 전체 조회 (T1, 탑승동, T2)
    # 전체 운항 현황 API는 터미널 ID가 다를 수 있어 P01, P02, P03을 순회합니다.
    terminals = {'T1': 'P01', '탑승동': 'P02', 'T2': 'P03'}
    
    for t_name, t_code in terminals.items():
        params = {
            "serviceKey": real_key,
            "type": "json",
            "searchTerminalId": t_code, # 여긴 파라미터 이름이 searchTerminalId 일 수 있음 (혹은 terminalId)
            "numOfRows": "100",
            "pageNo": "1"
        }
        
        # 파라미터 이름이 API마다 달라서 두 가지 방식으로 다 찔러봅니다.
        # 시도 A: terminalId
        try:
            params['terminalId'] = t_code
            response = requests.get(url, params=params, timeout=5)
            data = response.json()
            items = data['response']['body']['items']
            if not isinstance(items, list): items = [items]
            
            for item in items:
                if str(item.get('gate')) in target_gates:
                    item['terminal_name'] = t_name
                    all_flights.append(item)
        except:
            pass

    return pd.DataFrame(all_flights) if all_flights else pd.DataFrame()

# ==========================================
# 4. 화면 출력
# ==========================================
if not api_key_input:
    st.warning("사이드바에 인증키를 입력해주세요.")
else:
    with st.spinner('전체 운항 데이터 조회 중...'):
        df = get_flight_data(api_key_input, gate_input)
    
    if df.empty:
        st.error("데이터가 안 나옵니다. (가능성: 게이트에 비행기가 없거나, 키 등록 대기중)")
        st.info("혹시 모르니 아래 링크를 클릭해서 데이터가 뜨는지 확인해보세요.")
        
        # 직접 확인용 링크 생성
        real_key = unquote(api_key_input)
        test_link = f"http://apis.data.go.kr/B551177/statusOfAllFltDeOdp/getStatusOfAllFltDeOdp?serviceKey={real_key}&type=json&numOfRows=10&pageNo=1"
        st.markdown(f"[👉 클릭해서 외계어(데이터)가 나오는지 확인하기]({test_link})")
        
    else:
        st.success(f"성공! {len(df)}개의 비행편을 찾았습니다.")
        df = df.sort_values(by='scheduleDateTime')
        
        for index, row in df.iterrows():
            # 데이터 추출
            time_str = str(row.get('scheduleDateTime', ''))
            f_time = f"{time_str[8:10]}:{time_str[10:12]}" if len(time_str) >= 12 else "미정"
            remark = row.get('remark', '대기')
            flight_no = row.get('flightId', '')
            airline = row.get('airline', '')
            dest = row.get('airport', '')
            gate = row.get('gate', '?')
            
            # 색상 (출발 전용)
            color = "#e7f5ff" # 파랑(기본)
            emoji = "🛫"
            if "탑승" in remark: 
                color = "#d4edda" # 초록
                emoji = "🟢"
            elif "마감" in remark:
                color = "#f8d7da" # 빨강
                emoji = "🔴"

            st.markdown(f"""
            <div style="padding:15px; border-radius:10px; margin-bottom:10px; background-color:{color}; border:1px solid
