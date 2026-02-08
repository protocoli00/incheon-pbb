import streamlit as st
import requests
import pandas as pd
from urllib.parse import unquote, quote
from datetime import datetime

# ==========================================
# 1. 화면 설정
# ==========================================
st.set_page_config(page_title="PBB 현황판", page_icon="🛫", layout="centered")
st.title("🛫 PBB 현황판 (안정화)")
st.caption("서버 오류(500) 해결을 위해 데이터 요청량을 조절했습니다.")

# ==========================================
# 2. 사이드바 설정
# ==========================================
with st.sidebar:
    st.header("⚙️ 설정")
    # API 키 입력
    api_key_input = st.text_input("인증키 입력", type="password")
    
    # 💡 해결사 스위치 추가
    use_encoding = st.checkbox("데이터가 안 나오면 체크하세요 (키 변환)", value=False)
    
    # 터미널 (T1 기본)
    st.subheader("터미널")
    terminal_options = {'T1': 'P01', '탑승동': 'P02', 'T2': 'P03'}
    selected_terminals = st.multiselect("구역", list(terminal_options.keys()), default=['T1'])
    
    # 게이트
    st.subheader("게이트")
    gate_input = st.text_input("번호 (비워두면 전체)", value="")
    
    if st.button("새로고침"):
        st.rerun()

# ==========================================
# 3. 카운터 변환 함수
# ==========================================
def format_counter(text):
    if not text or text == "-" or text == "None": return "-"
    try:
        # 데이터 정제 (예: H01-H18)
        start_code = text.split('-')[0].strip()
        alpha = start_code[0] # H
        number = int(start_code[1:]) # 1
        
        # 1~18번은 1구역, 19번부터는 2구역
        suffix = "1" if number <= 18 else "2"
        return f"{alpha}{suffix} 카운터"
    except:
        return text

# ==========================================
# 4. 데이터 로직 (500 에러 방지)
# ==========================================
def get_flight_data(key_input, gate_input_str, terminals_to_check, use_enc):
    if not key_input: return pd.DataFrame(), None

    # [중요] 키 처리 로직 선택
    if use_enc:
        # 체크박스 ON: 인코딩된 키라고 가정하고 그대로 사용하거나 다시 인코딩
        # (보통 Decoding키를 넣고 이 옵션을 켜면 에러가 해결될 때가 있음)
        real_key = key_input 
    else:
        # 체크박스 OFF: Decoding(일반) 모드 (기본값)
        real_key = unquote(key_input)

    today_str = datetime.now().strftime("%Y%m%d")
    
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
            "serviceKey": real_key, 
            "type": "json",
            "terminalId": t_code, 
            "searchDate": today_str,
            "numOfRows": "100", # 👈 [핵심] 300 -> 100으로 줄임 (서버 폭주 방지)
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
                error_msg = f"서버 에러({res.status_code}): {res.text[:100]}"
        except Exception as e:
            error_msg = f"통신 에러: {e}"

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

    # 에러가 있으면 알려줌
    if err and df.empty:
        st.error(f"데이터를 못 가져왔습니다. ({err})")
        st.info("💡 사이드바에 있는 '데이터가 안 나오면 체크하세요' 박스를 눌러보세요.")
    
    elif df.empty:
        st.info("조건에 맞는 운항 스케줄이 없습니다.")
    else:
        # 시간순 정렬
        if 'scheduleDateTime' in df.columns:
            df = df.sort_values(by='scheduleDateTime')

        st.success(f"조회 성공: 총 {len(df)}건")

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
            
            # 색상 로직
            bg_color = "#ffffff"
            text_color = "#333"
            bottom_info = ""

            if row_type == '도착':
                bg_color = "#cce5ff"
                status_text = "도착"
                bottom_info = f"수하물: {str(row.get('carousel', '-'))}"
            else:
                bottom_info = f"Check-in: {conv_counter}"
                status_text = remark
                if "탑승" in remark: bg_color = "#d4edda"
                elif "마감" in remark or "Final" in remark: bg_color = "#f8d7da"
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
