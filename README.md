# 설농체 · Seolnong

일본의 한국어 안내판에서 발견한 글자 모양을 바탕으로 만든 한글 글꼴입니다. ‘ト’와 닮은 ㅏ와 낮고 옆으로 퍼지는 받침이 특징입니다. 간판, 제목, 짧은 문구에 어울립니다.

[글자 써 보기](https://dolsup.github.io/seolnong/) · [설농체 1.003 내려받기 (ZIP)](https://github.com/dolsup/seolnong/raw/refs/heads/main/downloads/Seolnong-1.003.zip) · [이용 안내](https://dolsup.github.io/seolnong/guide.html) · [갱신의 기록](https://dolsup.github.io/seolnong/#updates)

![설농체와 일본어·영어·한글 안내판 견본](assets/og.png)

## 사용하기

ZIP을 풀고 `Seolnong-Regular.ttf`를 설치하면 글꼴 목록에서 **설농체** 또는 **Seolnong**을 선택할 수 있습니다. Regular 한 굵기이며 현대 한글 11,172자, 현대 조합 자모와 호환 자모, 기본 영문·숫자, 전각 영숫자·기호, 안내판용 괄호·화살표·통화·단위 기호를 지원합니다. 한자·일본어·옛한글에는 다른 글꼴을 함께 사용하세요.

ㅎ·ㅊ의 꼭지는 기본적으로 가로입니다. OpenType 스타일 세트 **Upright tops (`ss01`)**를 켜면 두 자모의 꼭지가 세로로 바뀝니다.

### OpenType 기능

| 기능 | 동작 |
| --- | --- |
| `ss01` | ㅎ·ㅊ의 꼭지를 함께 세로로 바꿉니다. |
| `aalt` | 지원 앱의 글리프 패널 등에서 대체 자형을 고를 수 있습니다. |
| `pnum` / `tnum` | 반각 숫자를 비례 폭 / 같은 폭으로 바꿉니다. 기본 숫자는 같은 폭입니다. |
| `zero` | 숫자 0에 사선을 넣습니다. |
| `kern` / `vkrn` | 가로·세로 조판에서 영문과 문장부호의 특정 조합 간격을 보정합니다. |
| `vert` / `vrt2` | 세로쓰기에서 괄호·문장부호 등의 대체형을 사용합니다. |

세로쓰기용 메트릭을 포함합니다. 기능의 표시 이름과 선택 방법은 앱에 따라 다릅니다.

### 웹에서 쓰기

ZIP에 들어 있는 `Seolnong-Regular.woff2`를 사이트에 올리고 CSS에서 불러오세요.

```css
@font-face {
  font-family: "Seolnong";
  src: url("./Seolnong-Regular.woff2") format("woff2");
  font-weight: 400;
  font-style: normal;
  font-display: swap;
}

.sign {
  font-family: "Seolnong", sans-serif;
  font-synthesis: none;
  font-feature-settings: "ss01" 1;
}
```

위 예시는 세로 꼭지를 사용합니다. 가로 꼭지를 쓰려면 `"ss01" 0`으로 지정하세요.

비례 숫자와 사선 0에는 `font-variant-numeric: proportional-nums slashed-zero;`를 사용할 수 있습니다. 세로쓰기는 `writing-mode: vertical-rl; text-orientation: mixed;`로 지정합니다.

## 1.003의 변경

- 안내판에 쓰는 괄호, 엔 기호, 주의·도형·온도 기호, 대각선 화살표 등을 추가했습니다.
- 세로쓰기 위치와 세로용 문장부호를 설계했습니다.
- 대체 자형 선택, 비례 숫자·사선 0, 영문과 문장부호의 커닝을 추가했습니다.
- 밑줄·취소선과 영문 높이 메타데이터를 정리했습니다.
- 반복되는 윤곽을 공유하도록 저장해 TTF·WOFF2의 용량을 줄였습니다.
- 기존 한글의 윤곽·폭과 `ss01`의 의미는 유지했습니다.

## 소스에서 다시 만들기

Python 3.12 환경에서 실행하세요.

```sh
python -m pip install -r requirements.txt
python build.py
python verify.py
```

`fonts/`의 TTF·WOFF2와 `downloads/Seolnong-1.003.zip`을 다시 만듭니다. `verify.py`는 지원 문자, OpenType 기능, 한글 조합, 메트릭과 배포 파일을 검사합니다. 소개 페이지는 별도 빌드 없이 정적 파일로 서비스할 수 있습니다.

배포본의 바이트 단위 재현은 GitHub Actions와 같은 Linux x86-64 환경에서 `python verify.py --rebuild`로 확인합니다. 이 명령은 소스를 별도 디렉터리에서 다시 빌드해 TTF·WOFF2·ZIP을 비교합니다.

빌드 시 반복되는 윤곽을 합성 글리프의 구성요소로 공유합니다. 저장 구조를 바꾸기 전후의 점 좌표, 윤곽 순서와 메트릭이 같은지 검사합니다.

## 라이선스

설농체와 폰트 제작 소스는 [SIL Open Font License 1.1](OFL.txt)로 배포합니다. 개인·상업 이용, 임베딩, 수정과 재배포가 가능합니다. 재배포 시 저작권 고지와 라이선스 전문을 함께 제공하세요. 폰트 단독 판매는 금지됩니다.

소개 페이지에 쓰인 Kosugi Maru와 Arimo의 출처와 라이선스는 [별도 고지](licenses/README.md)에서 확인할 수 있습니다.
