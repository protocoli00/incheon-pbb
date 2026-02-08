import streamlit as st
import requests
import pandas as pd
from urllib.parse import unquote
from datetime import datetime

# ==========================================
# 1. 화면 기본 설정
# ==========================================
st.set_page_config(page_title="PBB 정밀진단", page_icon="🚑", layout="centered")
st.title("🚑 PBB 현황판 (진단모드)")
st.caption("갑자기 안 될 때 원인을 찾아내는 버전입니다.")

# ==========================================
# 2. 사이드바 설정
# ==========================================
with st.sidebar:
    st.header("⚙️ 설정")
    api_key_input = st.text_input("인증키 입력 (Decoding)", type="password")
    
    st.subheader("터미널")
    # T1을 기본값으로
    terminal_options = {'T1': 'P01', '탑승동': 'P02', 'T2': 'P03'}
    selected_terminals = st.multiselect("구역", list(terminal_options.keys()), default=['T1'])
    
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
        start_code = text.split('-')[0].strip()
        alpha = start_code[0]
        number = int(start_code[1:])
        suffix = "1" if number <= 18 else "2"
        return f"{alpha}{suffix} 카운터"
    except:
        return text

# ==========================================
# 4. 데이터 로직 (로그 기록 기능 추가)
# ==========================================
def get_flight_data(key_input, gate_input_str, terminals_to_check):
    if not key_input: return pd.DataFrame(), ["키를 입력해주세요."]

    real_key = unquote(key_input)
    today_str = datetime.now().strftime("%Y%m%d")
    
    target_gates = []
    if gate_input_str.strip():
        target_gates = [g.strip() for g in gate_input_str.split(',') if g.strip()]

    # 아까 성공했던 그 주소 (StatusOfFlights)
    base_url = "http://apis.data.go.kr/B551177/StatusOfFlights"
    url_dep = f"{base_url}/getFltDeparturesDeOdp"
    url_arr = f"{base_url}/getFltArrivalsDeOdp"
    
    all_flights = []
    logs = [] # 서버 응답을 기록할 일기장

    for t_name in terminals_to_check:
        t_code = terminal_options[t_name]
        
        params = {
            "serviceKey": real_key, "type": "json",
            "terminalId": t_code, "searchDate": today_str,
            "numOfRows": "200", "pageNo": "1"
        }

        # [출발 요청]
        try:
            res = requests.get(url_dep, params=params, timeout=10)
            # 로그 기록
            logs.append(f"[{t_name} 출발] 상태코드: {res.status_code}")
            if res.status_code != 200:
                 logs.append(f"👉 에러내용: {res.text[:300]}")
            
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
                    logs.append(f"[{t_name} 출발] 데이터 없음(items is empty/null)")
        except Exception as e:
            logs.append(f"[{t_name} 출발] 통신오류: {e}")

        # [도착 요청]
        try:
            res = requests.get(url_arr, params=params, timeout=10)
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

    return pd.DataFrame(all_flights), logs

# ==========================================
# 5. 화면 출력
# ==========================================
if not api_key_input:
    st.warning("👈 사이드바에 키를 입력해주세요.")
else:
    with st.spinner('서버와 통신 중...'):
        df, debug_logs = get_flight_data(api_key_input, gate_input, selected_terminals)

    # 결과가 없거나 에러가 났을 때 확인하는 곳
    with st.expander("🐞 서버 응답 내용 확인하기 (안 될 때 눌러보세요)"):
        st.write("서버가 뭐라고 했는지 보여줍니다:")
        for log in debug_logs:
            st.code(log)

    if df.empty:
        st.error("데이터가 안 보입니다.")
        st.info("위의 '서버 응답 내용 확인하기'를 눌러서 LIMITED_NUMBER(트래픽 초과)인지 확인해보세요.")
    else:
        if 'scheduleDateTime' in df.columns:
            df = df.sort_values(by='scheduleDateTime')

        st.success(f"총 {len(df)}건 조회 성공")

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
                bottom_info = f"수하물: {str(row.get('carousel', '-'))}"
                status_text = "도착"
            else:
                bottom_info = f"Check-in: {conv_counter}"
                status_text = remark
                if "탑승" in remark: bg_color = "#d4edda"
                elif "마감" in remark: bg_color = "#f8d7da"
                elif "지연" in remark: bg_color = "#fff3cd"
                elif "결항" in remark: bg_color = "#e2e3e5"

            st.markdown(f"""
            <div style="background-color:{bg_color}; padding:15px; margin-bottom:10px; border-radius:12px; border:1px solid #ddd;">
                <div style="display:flex; justify-content:space-between; margin-bottom:5px;">
                    <span style="font-size:24px; font-weight:bold;">{f_time}</span>
                    <span style="font-size:18px; font-weight:bold;">{status_text}</span>
                </div>
                <div style="font-size:20px; font-weight:bold;">
                    <span style="background:#333; color:white; padding:2px 8px; border-radius:5px;">G{gate}</span>
                    {flight_no}
                </div>
                <div style="margin-top:5px; border-top:1px dashed #aaa; padding-top:5px; text-align:right; font-weight:bold;">
                    {bottom_info}
                </div>
            </div>
            """, unsafe_allow_html=True)
