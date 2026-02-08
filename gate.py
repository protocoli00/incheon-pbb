import streamlit as st
import requests
import pandas as pd
from urllib.parse import unquote
from datetime import datetime

# ==========================================
# 1. 화면 기본 설정
# ==========================================
st.set_page_config(page_title="PBB 최종 해결", page_icon="✈️")
st.title("✈️ PBB 항공기 운항 (날짜 포함)")
st.caption("API 목록(getFlt...) + 오늘 날짜 자동 입력")

# ==========================================
# 2. 사이드바
# ==========================================
with st.sidebar:
    st.header("⚙️ 설정")
    # 키 입력
    api_key_input = st.text_input("인증키 입력 (Decoding 권장)", type="password")
    
    # 터미널 선택
    st.subheader("터미널")
    terminal_options = {'T1': 'P01', '탑승동': 'P02', 'T2': 'P03'}
    selected_terminals = st.multiselect("구역", list(terminal_options.keys()), default=list(terminal_options.keys()))
    
    # 게이트 입력
    st.subheader("게이트")
    gate_input = st.text_input("번호 (비워두면 전체)", value="")
    
    if st.button("데이터 가져오기"):
        st.rerun()

# ==========================================
# 3. 데이터 로직 (핵심)
# ==========================================
def get_flight_data(key_input, gate_input_str, terminals_to_check):
    if not key_input: return pd.DataFrame()

    real_key = unquote(key_input) # 키 보정
    today_str = datetime.now().strftime("%Y%m%d") # 오늘 날짜 (예: 20260208)
    
    # 게이트 정리
    target_gates = []
    if gate_input_str.strip():
        target_gates = [g.strip() for g in gate_input_str.split(',') if g.strip()]

    # 👇 [중요] 선생님이 주신 "API 목록"에 맞는 진짜 주소
    base_url = "http://apis.data.go.kr/B551177/StatusOfFlights"
    url_dep = f"{base_url}/getFltDeparturesDeOdp" # 출발
    url_arr = f"{base_url}/getFltArrivalsDeOdp"   # 도착
    
    all_flights = []

    for t_name in terminals_to_check:
        t_code = terminal_options[t_name]
        
        # 👇 [핵심] 날짜(searchDate)를 안 넣으면 에러가 날 수 있음!
        params = {
            "serviceKey": real_key,
            "type": "json",
            "terminalId": t_code,
            "searchDate": today_str, # 오늘 날짜 필수!
            "numOfRows": "100",
            "pageNo": "1"
        }

        # --- [1] 출발 ---
        try:
            res = requests.get(url_dep, params=params, timeout=5)
            if res.status_code == 200:
                data = res.json()
                items = data.get('response', {}).get('body', {}).get('items')
                if items:
                    if not isinstance(items, list): items = [items]
                    for item in items:
                        current_gate = str(item.get('gate', ''))
                        if not target_gates or current_gate in target_gates:
                            item['type'] = '출발'
                            item['terminal_name'] = t_name
                            all_flights.append(item)
        except: pass

        # --- [2] 도착 ---
        try:
            res = requests.get(url_arr, params=params, timeout=5)
            if res.status_code == 200:
                data = res.json()
                items = data.get('response', {}).get('body', {}).get('items')
                if items:
                    if not isinstance(items, list): items = [items]
                    for item in items:
                        current_gate = str(item.get('gate', ''))
                        if not target_gates or current_gate in target_gates:
                            item['type'] = '도착'
                            item['terminal_name'] = t_name
                            all_flights.append(item)
        except: pass

    return pd.DataFrame(all_flights) if all_flights else pd.DataFrame()

# ==========================================
# 4. 화면 출력
# ==========================================
if not api_key_input:
    st.warning("👈 키를 입력하세요.")
else:
    with st.spinner('데이터 조회 중...'):
        df = get_flight_data(api_key_input, gate_input, selected_terminals)

    if df.empty:
        st.error("데이터가 없습니다.")
        st.write("1. API 키가 아직 승인 대기 중일 수 있습니다. (1시간 소요)")
        st.write("2. '활용신청'이 제대로 안 되었을 수 있습니다.")
        
        # 👇 진단 링크 (날짜 포함)
        real_key = unquote(api_key_input)
        today = datetime.now().strftime("%Y%m%d")
        test_url = f"http://apis.data.go.kr/B551177/StatusOfFlights/getFltDeparturesDeOdp?serviceKey={real_key}&type=json&terminalId=P01&searchDate={today}&numOfRows=5&pageNo=1"
        st.markdown(f"[👉 클릭해서 데이터 확인하기 (테스트 링크)]({test_url})")
        
    else:
        if 'scheduleDateTime' in df.columns:
            df = df.sort_values(by='scheduleDateTime')

        count = len(df)
        msg = f"🔍 전체 조회: {count}건" if not gate_input.strip() else f"🔍 게이트 {gate_input}: {count}건"
        st.success(msg)

        for index, row in df.iterrows():
            row_type = row.get('type', '출발')
            gate = row.get('gate', '?')
            remark = row.get('remark', '예정')
            if not remark: remark = "예정"
            
            t_str = str(row.get('scheduleDateTime', ''))
            f_time = f"{t_str[8:10]}:{t_str[10:12]}" if len(t_str) >= 12 else "미정"
            
            flight_no = row.get('flightId', '-')
            airline = row.get('airline', '-')
            
            # 색상
            bg = "#e7f5ff" if row_type == '도착' else "#ffffff"
            icon = "🛬" if row_type == '도착' else "🛫"
            if row_type == '출발' and "탑승" in remark: bg = "#d4edda"; icon = "🟢"
            
            # HTML 출력
            st.markdown(f"""
            <div style="padding:15px; margin-bottom:10px; border-radius:10px; background-color:{bg}; border:1px solid #ddd;">
                <div style="font-weight:bold; font-size:18px; margin-bottom:5px;">
                    {f_time} | {remark}
                </div>
                <div style="font-size:16px;">
                    <span style="background:#333; color:white; padding:2px 6px; border-radius:4px;">G{gate}</span>
                    {flight_no}
                </div>
                <div style="color:#555; font-size:14px; margin-top:5px;">
                    {icon} {airline}
                </div>
            </div>
            """, unsafe_allow_html=True)
