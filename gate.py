import streamlit as st
import requests
import pandas as pd
from urllib.parse import unquote, quote

# ==========================================
# 1. 화면 기본 설정
# ==========================================
st.set_page_config(page_title="PBB 주소 탐지기", page_icon="📡")
st.title("📡 API 주소 자동 탐지기")
st.caption("선생님의 키에 딱 맞는 주소를 자동으로 찾아냅니다.")

# ==========================================
# 2. 사이드바 설정
# ==========================================
with st.sidebar:
    st.header("설정")
    api_key_input = st.text_input("인증키를 입력하세요", type="password")
    
    st.subheader("게이트 선택")
    gate_input = st.text_input("게이트 번호", value="10, 105, 230")
    
    st.markdown("---")
    st.caption("새로고침을 누르면 3가지 주소를 모두 테스트합니다.")
    if st.button("주소 찾기 및 새로고침"):
        st.rerun()

# ==========================================
# 3. 데이터 로직 (3중 테스트)
# ==========================================
def get_flight_data(key_input, gate_input_str):
    if not key_input: return pd.DataFrame(), "키를 입력해주세요."

    real_key = unquote(key_input) # 키 보정
    target_gates = [g.strip() for g in gate_input_str.split(',') if g.strip()]
    all_flights = []
    
    # 🕵️‍♂️ 테스트할 3가지 후보군 (인천공항 API 3대장)
    candidates = [
        {
            "name": "1. 항공기 운항정보 (StatusOfFlights)",
            "url_dep": "http://apis.data.go.kr/B551177/StatusOfFlights/getFltDeparturesDeOdp",
            "url_arr": "http://apis.data.go.kr/B551177/StatusOfFlights/getFltArrivalsDeOdp",
            "param_term": "terminalId"
        },
        {
            "name": "2. 전체 운항 현황 (statusOfAllFltDeOdp)",
            "url_dep": "http://apis.data.go.kr/B551177/statusOfAllFltDeOdp/getStatusOfAllFltDeOdp",
            "url_arr": "http://apis.data.go.kr/B551177/statusOfAllFltArOdp/getStatusOfAllFltArOdp",
            "param_term": "searchTerminalId"
        },
        {
            "name": "3. 여객기 운항 현황 (StatusOfPassengerFlightsOdp)",
            "url_dep": "http://apis.data.go.kr/B551177/StatusOfPassengerFlightsOdp/getPassengerDeparturesOdp",
            "url_arr": "http://apis.data.go.kr/B551177/StatusOfPassengerFlightsOdp/getPassengerArrivalsOdp",
            "param_term": "terminalId"
        }
    ]

    success_msg = ""
    terminals = {'T1': 'P01', '탑승동': 'P02', 'T2': 'P03'}

    # 후보군을 하나씩 순회하며 테스트
    for candidate in candidates:
        temp_flights = []
        is_success = False
        
        # 각 터미널 조회
        for t_name, t_code in terminals.items():
            params = {
                "serviceKey": real_key,
                "type": "json",
                candidate["param_term"]: t_code, # API마다 변수명이 다름
                "numOfRows": "20",
                "pageNo": "1"
            }
            
            # (1) 출발 조회 시도
            try:
                res = requests.get(candidate["url_dep"], params=params, timeout=3)
                if res.status_code == 200 and "response" in res.json():
                    is_success = True # 빙고! 찾았다
                    items = res.json()['response']['body']['items']
                    if items:
                        if not isinstance(items, list): items = [items]
                        for item in items:
                            if str(item.get('gate')) in target_gates:
                                item['type'] = '출발'
                                item['terminal_name'] = t_name
                                temp_flights.append(item)
            except: pass

            # (2) 도착 조회 시도 (성공한 경우에만)
            if is_success:
                try:
                    res = requests.get(candidate["url_arr"], params=params, timeout=3)
                    if res.status_code == 200:
                        items = res.json()['response']['body']['items']
                        if items:
                            if not isinstance(items, list): items = [items]
                            for item in items:
                                if str(item.get('gate')) in target_gates:
                                    item['type'] = '도착'
                                    item['terminal_name'] = t_name
                                    temp_flights.append(item)
                except: pass
        
        # 성공했다면 데이터를 저장하고 루프 종료 (더 이상 찾을 필요 없음)
        if is_success:
            all_flights = temp_flights
            success_msg = f"✅ 연결 성공! 선생님의 키는 **[{candidate['name']}]** 입니다."
            break # 탐색 종료

    return pd.DataFrame(all_flights), success_msg

# ==========================================
# 4. 화면 출력
# ==========================================
if not api_key_input:
    st.warning("👈 사이드바에 키를 입력해주세요.")
else:
    with st.spinner('3가지 주소를 모두 두드려보는 중...'):
        df, msg = get_flight_data(api_key_input, gate_input)
    
    if msg:
        st.success(msg) # 찾은 API 이름 보여주기
        
        if df.empty:
            st.warning("연결은 성공했는데, 지금 해당 게이트에 비행기가 없습니다.")
        else:
            # 시간순 정렬
            if 'scheduleDateTime' in df.columns:
                df = df.sort_values(by='scheduleDateTime')

            for index, row in df.iterrows():
                # 데이터 정리
                row_type = row.get('type', '출발')
                time_str = str(row.get('scheduleDateTime', ''))
                f_time = f"{time_str[8:10]}:{time_str[10:12]}" if len(time_str) >= 12 else "미정"
                
                remark = row.get('remark', '예정')
                if not remark: remark = "예정"
                
                flight_no = row.get('flightId', '-')
                airline = row.get('airline', '-')
                gate = row.get('gate', '?')
                airport = row.get('airport', '-')

                # 디자인 (색상)
                if row_type == '도착':
                    color = "#e7f5ff" # 파랑
                    icon = "🛬"
                    route = f"출발: {airport}"
                else:
                    if "탑승" in remark: color = "#d4edda"; icon = "🟢" # 초록
                    elif "마감" in remark: color = "#f8d7da"; icon = "🔴" # 빨강
                    else: color = "#ffffff"; icon = "🛫" # 흰색
                    route = f"목적: {airport}"

                # 카드 출력
                st.markdown(f"""
                <div style="padding:15px; margin-bottom:10px; border-radius:10px; background-color:{color}; border:1px solid #ccc;">
                    <div style="display:flex; justify-content:space-between;">
                        <span style="font-size:20px; font-weight:bold;">{f_time}</span>
                        <span style="font-size:16px; font-weight:bold;">{icon} {remark}</span>
                    </div>
                    <div style="margin:5px 0; font-size:18px;">
                        <span style="background:#333; color:white; padding:2px 8px; border-radius:5px;">G{gate}</span>
                        <b>{flight_no}</b>
                    </div>
                    <div style="color:#555; font-size:14px;">{airline} | {route}</div>
                </div>
                """, unsafe_allow_html=True)
                
    else:
        st.error("❌ 3가지 주소 모두 실패했습니다.")
        st.info("가능성 1: 키 발급 후 1시간이 아직 안 지남")
        st.info("가능성 2: '활용신청'이 승인되지 않음")
        
        # 최후의 수단: 직접 클릭 링크
        real_key = unquote(api_key_input)
        # 링크 생성 시 키를 인코딩해서 넣어야 안전함
        encoded_key = quote(real_key) 
        test_link = f"http://apis.data.go.kr/B551177/StatusOfFlights/getFltDeparturesDeOdp?serviceKey={encoded_key}&type=json&terminalId=P01&numOfRows=10&pageNo=1"
        st.markdown(f"[👉 여기를 클릭해서 데이터가 뜨는지 마지막으로 확인해보세요]({test_link})")
