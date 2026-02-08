import streamlit as st
import requests
import pandas as pd
from datetime import datetime
from urllib.parse import unquote # 👈 핵심: 키를 자동으로 고쳐주는 도구 추가

# ==========================================
# 1. 기본 설정
# ==========================================
st.set_page_config(page_title="PBB 멀티뷰", page_icon="🛫")
st.title("🛫 PBB 멀티 게이트 현황")

# ==========================================
# 2. 사이드바
# ==========================================
with st.sidebar:
    st.header("설정 메뉴")
    # API 키 입력 안내 강화
    api_key_input = st.text_input("API 인증키 (Encoding/Decoding 무관)", type="password")
    
    st.subheader("터미널 선택")
    terminal_options = {'T1': 'P01', '탑승동': 'P02', 'T2': 'P03'}
    selected_terminals = st.multiselect("터미널 선택", list(terminal_options.keys()), default=list(terminal_options.keys()))
    
    st.subheader("담당 게이트 (여러 개 가능)")
    gate_input = st.text_input("번호 입력 (쉼표로 구분)", value="10, 11, 12", help="예: 10, 105, 230")
    
    if st.button("새로고침"):
        st.rerun()

# ==========================================
# 3. 데이터 로직 (키 자동 보정 적용)
# ==========================================
def get_flight_data(key_input, gate_input_str, terminals_to_check):
    # 👇 [중요] 사용자가 어떤 키를 넣든 'Decoding' 상태로 변환해서 사용
    # 이렇게 하면 Encoding 키를 넣어도, Decoding 키를 넣어도 다 작동합니다.
    real_key = unquote(key_input) 

    url_dep = "http://apis.data.go.kr/B551177/StatusOfPassengerFlightsOdp/getPassengerDeparturesOdp"
    url_arr = "http://apis.data.go.kr/B551177/StatusOfPassengerFlightsOdp/getPassengerArrivalsOdp"
    
    target_gates = [g.strip() for g in gate_input_str.split(',') if g.strip()]
    all_flights = []

    for terminal_name in terminals_to_check:
        t_code = terminal_options[terminal_name]
        
        # [출발] 조회
        try:
            params = {"serviceKey": real_key, "type": "json", "terminalId": t_code, "numOfRows": "300", "pageNo": "1"}
            response = requests.get(url_dep, params=params)
            
            # 응답 데이터 확인 로직 강화
            if response.status_code == 200:
                data = response.json()
                if "response" in data and "body" in data["response"]:
                    items = data['response']['body']['items']
                    if not isinstance(items, list): items = [items] if items else []
                    
                    for item in items:
                        if str(item.get('gate')) in target_gates:
                            item['type'] = '출발'
                            item['terminal_name'] = terminal_name
                            all_flights.append(item)
        except Exception as e: pass

        # [도착] 조회
        try:
            params = {"serviceKey": real_key, "type": "json", "terminalId": t_code, "numOfRows": "300", "pageNo": "1"}
            response = requests.get(url_arr, params=params)
            
            if response.status_code == 200:
                data = response.json()
                if "response" in data and "body" in data["response"]:
                    items = data['response']['body']['items']
                    if not isinstance(items, list): items = [items] if items else []
                    
                    for item in items:
                        if str(item.get('gate')) in target_gates:
                            item['type'] = '도착'
                            item['terminal_name'] = terminal_name
                            all_flights.append(item)
        except Exception as e: pass

    return pd.DataFrame(all_flights) if all_flights else pd.DataFrame()

# ==========================================
# 4. 색상 설정
# ==========================================
def get_status_info(row_type, status):
    status = str(status)
    if row_type == '도착':
        if "도착" in status or "착륙" in status: return "🔵", "#e7f5ff"
        else: return "⚪", "#f8f9fa"
    else:
        if "탑승중" in status: return "🟢", "#e6fffa"
        elif "마감" in status or "Final" in status: return "🔴", "#fff5f5"
        elif "지연" in status: return "🟡", "#fff9db"
        elif "출발" in status: return "🔵", "#e7f5ff"
        else: return "⚪", "#f8f9fa"

# ==========================================
# 5. 화면 출력
# ==========================================
if not api_key_input:
    st.warning("API 키를 입력해주세요.")
else:
    st.markdown("""
    <style>
    .flight-card { padding: 15px; border-radius: 12px; margin-bottom: 10px; border: 1px solid #ddd; }
    .time-text { font-size: 24px; font-weight: bold; color: #333; }
    .status-text { font-size: 18px; font-weight: bold; float: right; }
    .gate-badge { background-color: #333; color: white; padding: 2px 8px; border-radius: 4px; font-size: 14px; font-weight: bold; margin-right: 5px;}
    </style>
    """, unsafe_allow_html=True)

    with st.spinner('데이터 조회 중... (키 자동 보정 적용됨)'):
        df_result = get_flight_data(api_key_input, gate_input, selected_terminals)

    if df_result.empty:
        st.info("조건에 맞는 비행 정보가 없거나, 키 승인이 아직 안 되었습니다.")
        st.caption("Tip: 공공데이터포털 승인은 신청 후 1~2시간 정도 걸릴 수 있습니다.")
    else:
        df_result = df_result.sort_values(by='scheduleDateTime')

        for index, row in df_result.iterrows():
            row_type = row['type']
            current_gate = row.get('gate', '?')
            time_str = str(row.get('scheduleDateTime', ''))
            f_time = f"{time_str[8:10]}:{time_str[10:12]}" if len(time_str) >= 12 else "미정"
            remark = row.get('remark', '') 
            flight_no = row.get('flightId', '')
            airline = row.get('airline', '')
            airport = row.get('airport', '')

            emoji, bg_color = get_status_info(row_type, remark)
            tag = "🛬 IN" if row_type == '도착' else "🛫 OUT"
            
            st.markdown(f"""
            <div class="flight-card" style="background-color: {bg_color};">
                <div style="display: flex; justify-content: space-between; align-items: center;">
                    <span class="time-text">{f_time}</span>
                    <span class="status-text">{emoji} {remark}</span>
                </div>
                <div style="margin: 5px 0;">
                    <span class="gate-badge">G{current_gate}</span> 
                    <span style="font-size: 18px; font-weight: bold;">{flight_no}</span>
                </div>
                <div style="font-size: 14px; color: #666;">
                    <b>{tag}</b> | {airline} ({airport})
                </div>
            </div>
            """, unsafe_allow_html=True)
