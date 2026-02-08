import streamlit as st
import requests
import pandas as pd
from urllib.parse import unquote
from datetime import datetime
import pytz # 한국 시간 계산용

# ==========================================
# 1. 화면 설정
# ==========================================
st.set_page_config(page_title="PBB 현황판", page_icon="🕰️", layout="centered")

# 한국 시간(KST) 구하기
KST = pytz.timezone('Asia/Seoul')
now_kst = datetime.now(KST)
time_str = now_kst.strftime("%H:%M:%S") # 시:분:초
date_str = now_kst.strftime("%Y년 %m월 %d일")

# 타이틀과 시계 배치
st.title("🛫 PBB 현황판")
st.markdown(f"""
<div style="
    text-align: center; 
    background-color: #f0f2f6; 
    padding: 10px; 
    border-radius: 10px; 
    margin-bottom: 20px; 
    border: 2px solid #dfe2e5;">
    <div style="font-size: 16px; color: #555;">{date_str}</div>
    <div style="font-size: 40px; font-weight: bold; color: #333; font-family: monospace;">{time_str}</div>
    <div style="font-size: 12px; color: #888;">(새로고침 기준 실시간)</div>
</div>
""", unsafe_allow_html=True)

# ==========================================
# 2. 사이드바 설정
# ==========================================
with st.sidebar:
    st.header("⚙️ 설정")
    api_key_input = st.text_input("인증키 입력", type="password")
    
    # 500 에러 해결사 (키 타입 변경)
    use_encoding = st.checkbox("데이터 안 나오면 체크(키 변환)", value=False)
    
    st.subheader("터미널")
    terminal_options = {'T1': 'P01', '탑승동': 'P02', 'T2': 'P03'}
    selected_terminals = st.multiselect("구역", list(terminal_options.keys()), default=['T1'])
    
    st.subheader("게이트")
    gate_input = st.text_input("번호 (비워두면 전체)", value="")
    
    # 버튼 누르면 재실행 (시간도 갱신됨)
    if st.button("새로고침 (시간갱신)"):
        st.rerun()

# ==========================================
# 3. 카운터 변환 함수 (H1/H2)
# ==========================================
def format_counter(text):
    if not text or text == "-" or text == "None": return "-"
    try:
        start_code = text.split('-')[0].strip()
        alpha = start_code[0] # H
        number = int(start_code[1:]) # 1
        suffix = "1" if number <= 18 else "2"
        return f"{alpha}{suffix} 카운터"
    except:
        return text

# ==========================================
# 4. 데이터 로직 (안정화 버전)
# ==========================================
def get_flight_data(key_input, gate_input_str, terminals_to_check, use_enc):
    if not key_input: return pd.DataFrame(), None

    # 키 보정 로직
    real_key = key_input if use_enc else unquote(key_input)
    today_str = datetime.now(KST).strftime("%Y%m%d") # 한국 날짜
    
    target_gates = []
    if gate_input_str.strip():
        target_gates = [g.strip() for g in gate_input_str.split(',') if g.strip()]

    base_url = "http://apis.data.go.kr/B551177/StatusOfFlights"
    url_dep = f"{base_url}/getFltDeparturesDeOdp"
    url_arr = f"{base_url}/getFltArrivalsDeOdp"
    
    all_flights = []
    error_msg = None

    for t_name in terminals_to_check:
        t_code = terminal_options[t_name]
        
        params = {
            "serviceKey": real_key, "type": "json",
            "terminalId": t_code, "searchDate": today_str,
            "numOfRows": "100", # 100개로 제한 (500 에러 방지)
            "pageNo": "1"
        }

        # [출발]
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
            else:
                error_msg = f"서버 응답코드: {res.status_code}"
        except Exception as e:
            error_msg = f"통신 오류: {e}"

        # [도착]
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

    return pd.DataFrame(all_flights), error_msg

# ==========================================
# 5. 화면 출력
# ==========================================
if not api_key_input:
    st.warning("👈 사이드바에 키를 입력해주세요.")
else:
    with st.spinner('데이터 조회 중...'):
        df, err = get_flight_data(api_key_input, gate_input, selected_terminals, use_encoding)

    if err and df.empty:
        st.error(f"데이터 조회 실패 ({err})")
        st.info("사이드바의 '데이터 안 나오면 체크' 박스를 눌러보세요.")
    
    elif df.empty:
        st.info("현재 조건에 맞는 운항 스케줄이 없습니다.")
    else:
        if 'scheduleDateTime' in df.columns:
            df = df.sort_values(by='scheduleDateTime')

        st.success(f"조회 성공: {len(df)}건")

        for index, row in df.iterrows():
            row_type = row.get('type', '출발')
            gate = row.get('gate', '?')
            remark = row.get('remark', '예정')
            if not remark: remark = "예정"
            
            t_str = str(row.get('scheduleDateTime', ''))
            f_time = f"{t_str[8:10]}:{t_str[10:12]}" if len(t_str) >= 12 else "미정"
            
            flight_no = row.get('flightId', '-')
            airline = row.get('airline', '-')
            
            # 카운터 변환
            raw_counter = row.get('chkinRange', '-')
            conv_counter = format_counter(raw_counter)
            
            # 디자인 로직
            bg_color = "#ffffff"
            bottom_info = ""

            if row_type == '도착':
                bg_color = "#cce5ff"
                status_text = "도착"
                bottom_info = f"수하물: {str(row.get('carousel', '-'))}"
            else:
                status_text = remark
                bottom_info = f"Check-in: {conv_counter}"
                if "탑승" in remark: bg_color = "#d4edda"
                elif "마감" in remark: bg_color = "#f8d7da"
                elif "지연" in remark: bg_color = "#fff3cd"
                elif "결항" in remark: bg_color = "#e2e3e5"

            st.markdown(f"""
            <div style="background-color:{bg_color}; padding:15px; margin-bottom:10px; border-radius:12px; border:1px solid #ddd; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
                <div style="display:flex; justify-content:space-between; margin-bottom:5px;">
                    <span style="font-size:24px; font-weight:800; color:#333;">{f_time}</span>
                    <span style="font-size:18px; font-weight:bold; color:#444;">{status_text}</span>
                </div>
                <div style="font-size:22px; font-weight:bold; margin-bottom:5px;">
                    <span style="background:#333; color:white; padding:2px 8px; border-radius:5px; margin-right:5px;">G{gate}</span>
                    {flight_no}
                </div>
                <div style="font-size:16px; color:#555; margin-bottom:8px;">
                    {airline}
                </div>
                <div style="border-top:2px dotted #aaa; padding-top:8px; text-align:right; font-weight:bold; font-size:18px;">
                    {bottom_info}
                </div>
            </div>
            """, unsafe_allow_html=True)
