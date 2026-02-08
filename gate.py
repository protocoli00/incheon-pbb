import streamlit as st
import requests
import pandas as pd
from urllib.parse import unquote
from datetime import datetime

# ==========================================
# 1. 화면 설정
# ==========================================
st.set_page_config(page_title="PBB 항공기 운항편", page_icon="✈️", layout="centered")
st.title("✈️ PBB 항공기 운항 현황")
st.caption("신청하신 [항공기 운항편 조회] API 전용 버전입니다.")

# ==========================================
# 2. 사이드바 설청
# ==========================================
with st.sidebar:
    st.header("설정 메뉴")
    
    # 키 입력
    api_key_input = st.text_input("인증키를 입력하세요", type="password")
    
    # 터미널 선택
    st.subheader("터미널 선택")
    terminal_options = {'T1': 'P01', '탑승동': 'P02', 'T2': 'P03'}
    selected_terminals = st.multiselect("조회할 구역", list(terminal_options.keys()), default=list(terminal_options.keys()))
    
    # 게이트 선택
    st.subheader("게이트 번호")
    gate_input = st.text_input("번호 입력 (쉼표로 구분)", value="10, 105, 230")
    
    if st.button("새로고침"):
        st.rerun()

# ==========================================
# 3. 데이터 조회 로직 (항공기 운항편 API)
# ==========================================
def get_flight_data(key_input, gate_input_str, terminals_to_check):
    if not key_input: return pd.DataFrame()

    # 키 보정
    real_key = unquote(key_input)
    
    # 게이트 정리
    target_gates = [g.strip() for g in gate_input_str.split(',') if g.strip()]
    all_flights = []

    # 👇 선생님이 알려주신 API 주소로 변경됨
    base_url = "http://apis.data.go.kr/B551177/StatusOfFlights"
    url_dep = f"{base_url}/getFltDeparturesDeOdp" # 출발
    url_arr = f"{base_url}/getFltArrivalsDeOdp"   # 도착

    for t_name in terminals_to_check:
        t_code = terminal_options[t_name]
        
        # 파라미터 (항공기 운항편 API 표준)
        params = {
            "serviceKey": real_key,
            "type": "json",
            "terminalId": t_code, # 혹은 searchTerminalId 일수도 있음 (둘 다 시도)
            "numOfRows": "100",
            "pageNo": "1"
        }

        # --- [1] 출발 데이터 조회 ---
        try:
            res = requests.get(url_dep, params=params, timeout=5)
            if res.status_code == 200:
                data = res.json()
                items = data.get('response', {}).get('body', {}).get('items')
                if items:
                    if not isinstance(items, list): items = [items]
                    for item in items:
                        # 게이트 번호 비교
                        if str(item.get('gate')) in target_gates:
                            item['type'] = '출발'
                            item['terminal_name'] = t_name
                            all_flights.append(item)
        except: pass

        # --- [2] 도착 데이터 조회 ---
        try:
            res = requests.get(url_arr, params=params, timeout=5)
            if res.status_code == 200:
                data = res.json()
                items = data.get('response', {}).get('body', {}).get('items')
                if items:
                    if not isinstance(items, list): items = [items]
                    for item in items:
                        if str(item.get('gate')) in target_gates:
                            item['type'] = '도착'
                            item['terminal_name'] = t_name
                            all_flights.append(item)
        except: pass

    return pd.DataFrame(all_flights) if all_flights else pd.DataFrame()

# ==========================================
# 4. 화면 출력
# ==========================================
if not api_key_input:
    st.warning("👈 사이드바에 인증키를 입력해주세요.")
elif not selected_terminals:
    st.warning("터미널을 선택해주세요.")
else:
    with st.spinner('항공기 운항 정보 가져오는 중...'):
        df = get_flight_data(api_key_input, gate_input, selected_terminals)
    
    if df.empty:
        st.error("데이터가 없습니다.")
        st.info("팁: 아직 키 승인이 안 났거나(1시간 소요), 게이트에 배정된 비행기가 없을 수 있습니다.")
        
        # 디버깅용 링크 (선생님 API 주소로 생성)
        real_key = unquote(api_key_input)
        test_link = f"http://apis.data.go.kr/B551177/StatusOfFlights/getFltDeparturesDeOdp?serviceKey={real_key}&type=json&terminalId=P01&numOfRows=10&pageNo=1"
        st.markdown(f"[👉 클릭해서 데이터 확인하기 (테스트 링크)]({test_link})")
        
    else:
        st.success(f"총 {len(df)}건의 항공기 운항 정보를 찾았습니다.")
        
        # 시간순 정렬
        if 'scheduleDateTime' in df.columns:
            df = df.sort_values(by='scheduleDateTime')
            
        for index, row in df.iterrows():
            row_type = row.get('type', '출발')
            # 시간 포맷 (YYYYMMDDHHMM -> HH:MM)
            time_str = str(row.get('scheduleDateTime', ''))
            f_time = f"{time_str[8:10]}:{time_str[10:12]}" if len(time_str) >= 12 else "미정"
            
            # 변경 시간 (지연 확인용)
            est_str = str(row.get('estimatedDateTime', ''))
            f_est = f"{est_str[8:10]}:{est_str[10:12]}" if len(est_str) >= 12 else ""
            
            remark = row.get('remark', '예정') # 현황 정보
            if not remark: remark = "예정"
            
            flight_no = row.get('flightId', '-')
            airline = row.get('airline', '-')
            airport = row.get('airport', '-')
            gate = row.get('gate', '?')
            
            # 색상 로직
            if row_type == '도착':
                bg_color = "#e7f5ff" # 파랑
                icon = "🛬 IN"
                route_str = f"출발지: {airport}"
            else:
                if "탑승" in remark:
                    bg_color = "#d4edda" # 초록
                    icon = "🟢 OUT"
                elif "마감" in remark:
                    bg_color = "#f8d7da" # 빨강
                    icon = "🔴 OUT"
                else:
                    bg_color = "#ffffff" # 흰색
                    icon = "🛫 OUT"
                route_str = f"목적지: {airport}"

            # 변경 시간 표시 로직
            time_display = f_time
            if f_est and f_est != f_time:
                time_display = f"<span style='text-decoration:line-through; color:#999; font-size:16px;'>{f_time}</span> → <span style='color:#d63384;'>{f_est}</span>"

            # 카드 출력
            st.markdown(f"""
            <div style="padding:15px; margin-bottom:10px; border-radius:10px; background-color:{bg_color}; border:1px solid #ccc; box-shadow:2px 2px 5px #eee;">
                <div style="display:flex; justify-content:space-between; align-items:center;">
                    <span style="font-size:22px; font-weight:bold;">{time_display}</span>
                    <span style="font-size:16px; font-weight:bold;">{remark}</span>
                </div>
                <div style="font-size:18px; margin:5px 0;">
                    <span style="background:#333; color:#fff; padding:2px 8px; border-radius:5px;">G{gate}</span>
                    <b>{flight_no}</b>
                </div>
                <div style="font-size:14px; color:#555;">
                    <b>{icon}</b> | {airline} ({route_str})
                </div>
            </div>
            """, unsafe_allow_html=True)
