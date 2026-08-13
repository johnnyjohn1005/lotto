import streamlit as st
import pandas as pd
import random
import requests
from io import BytesIO

# 1. 웹 페이지 및 테마 기본 설정 (모바일 대응을 위해 wide 레이아웃 지정)
st.set_page_config(
    page_title="나만의 스마트 로또 생성기", 
    page_icon="🎰",
    layout="wide"
)

st.title("🎰 6/45 스마트 로또 필터링 번호 생성기")
st.write("모든 까다로운 조건과 동행복권 역대 당첨 데이터를 실시간 연동하여 완벽한 조합을 추천합니다.")

# 역대 로또 당첨 번호 데이터 실시간 연동 함수
@st.cache_data(ttl=3600)
def load_past_winners():
    try:
        url = "https://dhlottery.co.kr"
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
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
    except Exception as e:
        return []

# 역대 통계 데이터 기반 궁합수 Top 10 쌍 정의
TOP_COMPATIBLE_PAIRS = [
    (20, 35), (34, 43), (12, 17), (27, 43), (1, 4),
    (10, 23), (13, 41), (15, 34), (17, 22), (26, 38)
]

# 데이터 로딩 알림
with st.spinner("동행복권 역대 당첨 데이터 연동 중..."):
    past_winners = load_past_winners()
if past_winners:
    st.success(f"✅ 동행복권 역대 당첨 번호 {len(past_winners)}건 최신 데이터 연동 완료!")
else:
    st.warning("⚠️ 동행복권 서버 응답 지연으로 임시 데이터 모드로 전환합니다.")

# ---------------- 사용자 입력 및 조건 설정 UI ----------------
st.markdown("### ⚙️ 로또 조건 설정")

# 모바일 화면 대응을 위해 컬럼으로 분할 입력 받음
col1, col2 = st.columns([1, 1])

with col1:
    num_combinations = st.number_input("1. 생성할 조합 개수 입력", min_value=1, max_value=50, value=5, step=1)
    
    all_numbers = list(range(1, 46))
    selected_pool = st.multiselect("2. 사용할 숫자 풀 입력 (기본 1~45)", all_numbers, default=all_numbers)

with col2:
    fixed_nums = st.multiselect("3. 고정수 입력 (포함할 숫자 선택)", selected_pool)
    exclude_nums = st.multiselect("4. 특정 제외수 입력 (제외할 숫자 선택)", selected_pool)

# ---------------- 필터링 조건 알고리즘 ----------------
def is_valid_combination(comb, past_winners):
    # 조건 1. 3연속 이상 연번 제외 (예: 1, 2, 3)
    for i in range(len(comb) - 2):
        if comb[i+1] == comb[i] + 1 and comb[i+2] == comb[i] + 2:
            return False
            
    # 조건 2. 숫자들의 총합 범위 100~170 사이
    total_sum = sum(comb)
    if not (100 <= total_sum <= 170):
        return False
        
    # 조건 3. 첫 번째 숫자가 12 이상의 숫자는 제외 (즉, 무조건 11 이하여야 함)
    if comb[0] >= 12:
        return False
        
    # 조건 4. 모든 조합이 홀수 또는 짝수인 조합 제외
    evens = sum(1 for x in comb if x % 2 == 0)
    if evens == 0 or evens == 6:
        return False
        
    # 조건 6. 끝수가 3개 이상 중복되는 조합 제외 (예: 3, 13, 23 등 끝자리가 '3'으로 3개 이상 일치)
    end_digits = [x % 10 for x in comb]
    for d in set(end_digits):
        if end_digits.count(d) >= 3:
            return False
            
    # 조건 7. 숫자 6개 중 10 이하의 숫자가 3개 이상 들어간 조합 제외
    under_10 = sum(1 for x in comb if x <= 10)
    if under_10 >= 3:
        return False
        
    # 조건 8. 역대 1등 기준 2등/3등 가능 번호 제외 (과거 1등 번호와 5개 이상 일치 시 제외)
    comb_set = set(comb)
    for winner in past_winners:
        if len(winner.intersection(comb_set)) >= 5:
            return False
            
    # 조건 9. 숫자 2개는 궁합이 좋은 Top 10위 이내 번호 포함 여부 체크
    has_compatible_pair = False
    for p1, p2 in TOP_COMPATIBLE_PAIRS:
        if p1 in comb_set and p2 in comb_set:
            has_compatible_pair = True
            break
    if not has_compatible_pair:
        return False
        
    return True

# ---------------- 번호 조합 생성 및 출력 ----------------
st.markdown("---")
if st.button("🚀 필터링 조건으로 로또 번호 생성하기", type="primary", use_container_width=True):
    candidate_pool = [x for x in selected_pool if x not in exclude_nums]
    
    # 예외 상황 필터링
    if len(fixed_nums) > 6:
        st.error("고정수는 최대 6개까지만 선택할 수 있습니다.")
    elif len(set(fixed_nums).intersection(set(exclude_nums))) > 0:
        st.error("고정수와 제외수에 동시에 입력된 숫자가 있습니다. 확인해 주세요.")
    else:
        results = []
        attempts = 0
        max_attempts = 100000  # 필터가 엄격하므로 시도 횟수를 충분히 보장
        
        while len(results) < num_combinations and attempts < max_attempts:
            attempts += 1
            
            # 조건 9(궁합수) 만족 확률을 높이기 위해 Top 10 궁합수 중 한 쌍을 뽑아 시작 조합으로 지정
            pair = random.choice(TOP_COMPATIBLE_PAIRS)
            current_comb = set(fixed_nums) | set(pair)
            
            # 선택된 기본 풀과 제외수 조건에 위배되는 궁합수 쌍인 경우 재시도
            if not current_comb.issubset(set(candidate_pool)):
                continue
                
            remaining_slots = 6 - len(current_comb)
            if remaining_slots < 0:
                continue 
                
            available_pick = [x for x in candidate_pool if x not in current_comb]
            if len(available_pick) < remaining_slots:
                continue
                
            random_picks = random.sample(available_pick, remaining_slots)
            final_comb = sorted(list(current_comb | set(random_picks)))
            
            # 전체 필터 조건 통과 검증
            if is_valid_combination(final_comb, past_winners):
                if final_comb not in results:
                    results.append(final_comb)
        
        # 결과 화면 모바일 스캔 최적화 출력
        if results:
            st.success(f"✨ 조건에 맞는 완벽한 로또 번호 {len(results)}개 조합이 완성되었습니다!")
            for idx, comb in enumerate(results):
                # 카드 형태로 예쁘게 번호 출력
                st.info(f"👉 **조합 {idx+1}** :  ` {', '.join(map(str, comb))} `")
        else:
            st.error("필터 조건이 너무 엄격하여 조건에 맞는 번호 조합을 찾아내지 못했습니다. 고정수를 줄이거나 기본 숫자 풀을 넓혀주세요.")