# sk210 Final API

교재 269~270쪽 종합 실습입니다. 제공된 `00.sample-container/02.fastapi-backend-v2.0` FastAPI 예제의 사용자 CRUD, 상태 변경, Prometheus 기능을 가져왔습니다.

`main` 변경 → Jenkins 테스트 → Docker BuildKit 이미지 빌드·Harbor 푸시 → `gitops` 브랜치 이미지 태그 갱신 → ArgoCD 자동 배포 순서로 동작합니다.

## 구성

| 항목 | 값 |
|---|---|
| Git 저장소 | `https://github.com/kimgwang-hyeon/sk210-devops-final` |
| 소스 / 배포 브랜치 | `main` / `gitops` |
| 이미지 | `skala-registry.skala-ai.com/class-7/sk210-final-api` |
| 네임스페이스 | `class-7` |
| Deployment·Service·Ingress·ArgoCD Application | `sk210-final-api` |
| 서비스 주소 | `https://sk210-final.class-7.skala-ai.com` |
| ArgoCD 프로젝트 / 경로 | `class-7` / `kustomize/overlays/dev` |

`bootstrap`은 배포 전 표시값입니다. 최초 CI가 실제 이미지 태그로 바꾼 `gitops` 브랜치를 생성한 뒤 ArgoCD Application을 등록합니다. `main`의 표시값을 직접 배포하지 않습니다.

## 로컬 실행과 검사

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements-dev.txt
python -m unittest discover -s tests -v
python fastserver.py --port 8080
```

Docker로도 검증할 수 있습니다.

```bash
docker buildx build --target test --load -t sk210-final-api:test .
docker buildx build --target runtime --load -t sk210-final-api:local .
docker run --rm -p 8080:8080 sk210-final-api:local
kubectl kustomize kustomize/overlays/dev
```

## Jenkins

현재 실습의 로컬 Jenkins는 Docker 소켓과 `docker buildx`, `git`, `kustomize`를 갖춘 실행 노드를 사용합니다. `Jenkinsfile-CI-buildkit`는 이 환경에서 BuildKit으로 Linux AMD64 이미지를 생성합니다.

1. 개인 Pipeline Job을 생성하고 Pipeline script from SCM을 선택합니다.
2. 위 Git 저장소, `*/main`, `Jenkinsfile-CI-buildkit`을 지정합니다.
3. Git credential은 Username with password 형식의 `sk210-github-id`입니다. PAT는 이 저장소의 **Contents 읽기·쓰기** 권한이 필요합니다.
4. Harbor credential은 기존 `skala-image-registry-id`를 사용합니다.
5. 최초 빌드를 실행하고 `ci-result.json`의 이미지 태그와 소스·GitOps 커밋을 확인합니다.
6. GitHub에서 외부 접근 가능한 Jenkins의 `/github-webhook/` 주소를 등록하면 `main` push가 빌드를 시작합니다. 로컬 전용 Jenkins 주소는 GitHub에서 접근할 수 없으므로 수동 실행 또는 별도 공개 연결이 필요합니다.

인증 정보는 Jenkins에서만 주입합니다. 로그의 shell tracing을 끈 상태에서 처리하며, Docker 설정과 Git 인증 도우미는 작업별 임시 디렉터리에 만들고 삭제합니다. 공유 Git 설정이나 다른 작업의 이미지를 변경하지 않습니다.

## ArgoCD와 검증

최초 CI 완료 후 기존 ArgoCD의 `class-7` 프로젝트에서 `argocd/application.yaml`과 같은 설정으로 등록합니다. 공개 Git 저장소 읽기에는 저장소 PAT가 필요하지 않습니다. 기존 `harbor-registry-secret`, `public-nginx`, `wildcard-class-7-skala-ai-com-tls`를 재사용합니다.

ArgoCD가 `Synced / Healthy`가 되면 다음을 확인합니다.

```bash
curl -fsS https://sk210-final.class-7.skala-ai.com/api/version
curl -fsS https://sk210-final.class-7.skala-ai.com/python/health/readiness
curl -fsS https://sk210-final.class-7.skala-ai.com/api/users
```

`/api/version`의 `source_revision`이 빌드한 `main` 커밋과 같아야 합니다. 이후 소스를 바꾸고 다음 CI를 실행하여 버전이 바뀌는지 확인합니다.

사용자 데이터는 메모리에만 저장되는 교육용 예제이며 Pod 재시작 시 초기화됩니다. 홈 화면에서 준비 상태를 바꾸면 readiness 결과가 바뀌고, 서버 장애 상태를 선택하면 liveness 실패로 Pod가 재시작됩니다.
