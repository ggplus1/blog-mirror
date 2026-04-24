# blog-mirror

네이버 블로그 `ggplus1`(연약지반 전문 공사업체 금강플러스) 글을 구글 검색에 노출시키기 위한 미러 사이트 자동화.

- 미러 사이트: https://ggplus1.github.io/blog-mirror/
- 원본 블로그: https://blog.naver.com/ggplus1

## 동작 방식

1. 매일 한국시간 오전 9시, GitHub Actions 가 `scripts/sync.py` 실행
2. 네이버 블로그 RSS(`https://rss.blog.naver.com/ggplus1.xml`)에서 최신 글 20개 수집
3. 신규 글이 있으면 `posts/{글번호}.html` 로 미러 페이지 생성
4. `index.html`, `sitemap.xml` 재생성
5. 변경사항을 저장소에 자동 커밋/푸시 → GitHub Pages 가 자동 배포
6. 구글이 sitemap.xml 을 주기적으로 크롤링하여 색인

## 파일 구조

```
blog-mirror/
├── scripts/sync.py          # 메인 스크립트
├── templates/
│   ├── index.html.j2        # 홈페이지 템플릿
│   └── post.html.j2         # 개별 글 템플릿
├── posts/                   # 자동 생성되는 미러 HTML (수동 편집 X)
├── posts_index.json         # 처리한 글 목록 (수동 편집 X)
├── index.html               # 자동 생성 (수동 편집 X)
├── sitemap.xml              # 자동 생성 (수동 편집 X)
├── robots.txt               # 자동 생성 (수동 편집 X)
├── requirements.txt
└── .github/workflows/sync.yml
```

## 최초 설정 체크리스트

### 1. GitHub 저장소 설정
- [x] `ggplus1/blog-mirror` 저장소 생성 (Public)
- [ ] Settings → Pages → Source: `Deploy from a branch`, Branch: `main` / `/ (root)`
- [ ] Settings → Actions → General → Workflow permissions: **Read and write permissions** 체크
  - 이게 안 켜져 있으면 Actions 가 커밋을 푸시하지 못합니다.

### 2. 첫 실행
- Actions 탭 → "Sync Naver Blog to GitHub Pages" → **Run workflow** 버튼 수동 클릭
- 1~2분 후 저장소에 `index.html`, `posts/*.html`, `sitemap.xml` 생성되었는지 확인
- 브라우저로 `https://ggplus1.github.io/blog-mirror/` 접속해서 정상 표시 확인

### 3. Search Console 에 sitemap 제출
- https://search.google.com/search-console → 속성 선택
- 좌측 메뉴 `Sitemaps` → 새 사이트맵 추가 → `sitemap.xml` 입력 → 제출
- 며칠 내로 "성공" 상태가 되어야 함

## 색인 상태 확인

구글에서 다음 검색을 주기적으로 실행:

```
site:ggplus1.github.io
```

첫 주에는 1~5개, 한 달 후에는 대부분의 글이 잡혀야 정상입니다.

## 스케줄 변경

`.github/workflows/sync.yml` 의 cron 값을 수정.

- `"0 0 * * *"`  → 매일 UTC 00:00 (KST 09:00)
- `"0 0 * * 1,4"` → 매주 월·목 KST 09:00
- `"0 */6 * * *"` → 6시간마다

## 문제 해결

**Actions 가 실패**: Actions 탭에서 실패한 실행 → 로그 확인. RSS 일시 장애일 가능성이 높음. 수동으로 다시 실행.

**글이 안 올라옴**: 네이버 블로그 관리 → 기본 설정 → 검색엔진 최적화 → "수집 허용" 상태인지 재확인.

**구글에 안 잡힘**: Search Console 에서 해당 URL 을 `URL 검사` 도구에 넣고 "색인 생성 요청". 주 1~2회 반복.

**제목/본문이 깨짐**: 네이버 RSS 는 본문이 잘려 올 수 있음. 전체가 아니라 요약만 실릴 경우에도 SEO 에는 충분함.

## 수동으로 돌려보려면

로컬에서 테스트:

```bash
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python scripts/sync.py
```
