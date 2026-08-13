import streamlit as st
import pandas as pd
import random
import requests
from io import BytesIO

# 1. 웹 페이지 레이아웃 설정
st.set_page_config(page_title="프리미엄 필터링 로또 생성기", page_icon="🎰", layout="wide")
st.title("🎰 프리미엄 로또 6/45 필터링 조합 생성기")
st.caption("사용자가 입력한 지난주 번호를 바탕으로 제외/포함 조건을 실시간 필터링하여 최적의 조합을 선별합니다.")

# 역대 로또 당첨 데이터 다운로드 (조건 8: 1등 기준 2, 3등 모든 가능 조합 필터링용)
@st.cache_data(ttl=3600)
def load_all_past_winners():
    try:
        url = "https://dhlottery.co.kr"
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(url, headers=headers, timeout=10)
        df = pd.read_excel(BytesIO(response.content), skiprows=2)
        winners = []
        for _, row in df.iterrows():
            try:
                nums = {int(row['당첨번호1']), int(row['당첨번호2']), int(row['당첨번호3']), 
                        int(row['당첨번호4']), int(row['당첨번호5']), int(row['당첨번호6'])}
                winners.append(nums)
            except:
                continue
        return winners
    except:
        return []

# 데이터 통계 기반 역대 가장 많이 함께 나온 궁합이 좋은 번호 TOP 20 쌍
TOP_20_COMPATIBLE_PAIRS = [
    (20, 35), (34, 43), (12, 17), (27, 43), (1, 4), (10, 23), (13, 41), (15, 34), (17, 22), (26, 38),
    (3, 11), (5, 29), (8, 22), (14, 40), (18, 37), (21, 26), (25, 31), (33, 39), (38, 45), (42, 44)
]

# 역대 데이터 연동
with st.spinner("동행복권 역대 당첨 통계 데이터를 동기화하고 있습니다..."):
    past_winners = load_all_past_winners()

if past_winners:
    st.success(f"✅ 동행복권 역대 당첨 번호 {len(past_winners)}건 연동 완료!")

# ---------------- 대화형 사용자 입력 UI ----------------
st.markdown("### ⚙️ 번호 조합 추출 기본 설정")

# 5번 조건: 지난주 당첨된 로또번호 직접 입력 구역 (사이드바)
st.sidebar.markdown("### 📢 5. 지난주 당첨 번호 직접 입력")
all_numbers_list = list(range(1, 46))
last_nums_input = st.sidebar.multiselect("지난주 당첨 번호 6개 선택", all_numbers_list, default=[1, 2, 3, 4, 5, 6], max_selections=6)
last_bonus_input = st.sidebar.selectbox("지난주 보너스 번호 1개 선택", [x for x in all_numbers_list if x not in last_nums_input])

st.sidebar.markdown("---")
st.sidebar.markdown("**입력된 지난주 번호:**")
st.sidebar.markdown(f"👉 번호: ` {', '.join(map(str, last_nums_input))} `")
st.sidebar.markdown(f"👉 보너스: ` {last_bonus_input} `")

col1, col2 = st.columns(2)

with col1:
    # 1~2번 조건: 숫자 개수 선택 및 숫자 풀 입력
    num_combinations = st.number_input("1 & 2. 생성할 랜덤 조합의 개수 설정", min_value=1, max_value=50, value=5, step=1)
    selected_pool = st.multiselect("2. 기본 숫자 풀 지정 (1~45 사이 번호 입력/삭제)", all_numbers_list, default=all_numbers_list)

with col2:
    # 3~4번 조건: 고정수 및 제외수 입력 검사기
    fixed_nums = st.multiselect("3. 고정수 지정 체크 (포함하고 싶은 숫자 선택)", selected_pool)
    exclude_nums = st.multiselect("4. 특정 제외수 지정 체크 (제외하고 싶은 숫자 선택)", selected_pool)

# ---------------- 복합 핵심 조건 필터 함수 ----------------
def is_valid_combination(comb, past_winners, last_nums, last_bonus):
    # 조건 1. 3연속 이상 연번 제외
    for i in range(len(comb) - 2):
        if comb[i+1] == comb[i] + 1 and comb[i+2] == comb[i] + 2:
            return False
            
    # 조건 2. 숫자들의 총합 범위는 100~180 사이
    if not (100 <= sum(comb) <= 180):
        return False
        
    # 조건 3. 첫 번째 숫자가 12 이상인 조합 제외
    if comb[0] >= 12:
        return False
        
    # 조건 4. 모든 조합이 홀수(6:0) 또는 짝수(0:6)인 올멸 조합 제외
    evens = sum(1 for x in comb if x % 2 == 0)
    if evens == 0 or evens == 6:
        return False
        
    # 조건 6. 끝수(일의 자리)가 3개 이상 중복되는 조합 제외
    end_digits = [x % 10 for x in comb]
    for d in set(end_digits):
        if end_digits.count(d) >= 3:
            return False
            
    # 조건 7. 6개 숫자 중 10 이하의 숫자가 3개 이상 포함된 조합 제외
    if sum(1 for x in comb if x <= 10) >= 3:
        return False
        
    # 조건 8. 역대 1등 기준 2등/3등 배출 가능 조합 일절 제외 (과거 당첨번호 세트와 5개 이상 겹침 차단)
    comb_set = set(comb)
    for winner in past_winners:
        if len(winner.intersection(comb_set)) >= 5:
            return False
            
    # 조건 9. 추출 번호 중 최소 숫자 2개는 궁합이 좋은 번호 TOP 20위 내 번호쌍을 포함
    has_compatible_pair = False
    for p1, p2 in TOP_20_COMPATIBLE_PAIRS:
        if p1 in comb_set and p2 in comb_set:
            has_compatible_pair = True
            break
    if not has_compatible_pair:
        return False
        
    # 조건 10. 입력한 지난주 당첨번호 + 보너스번호 총 7개 중 '정확히 1개만' 포함 (2개 이상 진입 차단)
    last_week_total_pool = set(last_nums) | {last_bonus}
    intersect_count = len(last_week_total_pool.intersection(comb_set))
    if intersect_count != 1:
        return False
        
    return True

# ---------------- 실시간 알고리즘 연산 및 마크다운 출력 ----------------
st.markdown("---")
if st.button("🚀 필터링 규격 적용하여 조합 생성하기", type="primary", use_container_width=True):
    if len(last_nums_input) != 6:
        st.error("오류: 지난주 당첨 번호는 반드시 6개를 선택하셔야 필터링이 정상 동작합니다.")
    elif len(fixed_nums) > 6:
        st.error("고정수는 6개 이하로만 구성할 수 있습니다.")
    elif len(set(fixed_nums).intersection(set(exclude_nums))) > 0:
        st.error("고정수 목록과 제외수 목록에 공통된 숫자가 존재합니다.")
    else:
        candidate_pool = [x for x in selected_pool if x not in exclude_nums]
        last_week_total_list = list(set(last_nums_input) | {last_bonus_input})
        
        results = []
        attempts = 0
        max_attempts = 300000  # 필터 조건 만족을 위한 연산 루프 상한선
        
        while len(results) < num_combinations and attempts < max_attempts:
            attempts += 1
            
            # 조건 9와 조건 10 충족률을 끌어올리기 위한 조기 결합 초기셋 세팅
            random_pair = random.choice(TOP_20_COMPATIBLE_PAIRS)
            random_last_one = random.choice(last_week_total_list)
            
            current_comb = set(fixed_nums) | set(random_pair) | {random_last_one}
            
            # 사전에 선택된 기본 풀을 벗어나거나 제외수에 해당하면 패스
            if not current_comb.issubset(set(candidate_pool)):
                continue
                
            rem_slots = 6 - len(current_comb)
            if rem_slots < 0:
                continue
                
            available_pick = [x for x in candidate_pool if x not in current_comb]
            if len(available_pick) < rem_slots:
                continue
                
            random_picks = random.sample(available_pick, rem_slots)
            final_comb = sorted(list(current_comb | set(random_picks)))
            
            # 최종 필터 조건 검증
            if is_valid_combination(final_comb, past_winners, last_nums_input, last_bonus_input):
                if final_comb not in results:
                    results.append(final_comb)
        
        # UI 출력 및 지난주 번호 진하게(Bold) 마크업 처리
        if results:
            st.success(f"🎯 모든 필터 조건을 통과한 최종 {len(results)}개 로또 조합입니다.")
            
            last_week_total_set = set(last_nums_input) | {last_bonus_input}
            
            for idx, comb in enumerate(results):
                formatted_numbers = []
                for n in comb:
                    # 조건 10 준수 확인 및 지난주 번호 진하게 표시
                    if n in last_week_total_set:
                        formatted_numbers.append(f"**{n}**")  
                    else:
                        formatted_numbers.append(str(n))
                        
                display_text = ", ".join(formatted_numbers)
                st.markdown(f"🔹 **조합 {idx+1}** &nbsp;&nbsp;➔ &nbsp;&nbsp; [ {display_text} ]")
                
            st.caption(f"안내: 총 {attempts:,}회의 필터링 시도 끝에 조건에 부합하는 조합을 추출했습니다.")
        else:
            st.error("조건이 너무 촘촘하여 규격에 들어맞는 번호 조합을 완성하지 못했습니다. 입력 데이터의 풀을 넓혀주세요.")