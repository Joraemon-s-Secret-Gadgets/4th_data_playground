# Overview

이 wiki는 향수 데이터 크롤링 프로젝트의 팀 내부 지식 기반입니다.

공식몰, Fragrantica, Fraganty, Persona-L export에서 수집한 향수 데이터를 하나의 JSON 계약으로 정규화하는 방식과 운영 규칙을 정리합니다.

## Scope

- 브랜드별 향수 데이터 크롤러 관리
- 정규화된 `data/*.json` 산출물 관리
- DeepL 기반 선택적 한국어 이름 번역
- 데이터 계약, 테스트, 커밋/브랜치 컨벤션 관리

## Directory Policy

- `backend/pipelines/`: 크롤러, 파서, 변환기, 공통 정규화 로직
- `backend/tests/`: 크롤러와 데이터 계약 테스트
- `data/`: 정규화된 JSON 산출물
- `docs/`: 설계 문서, 데이터 계약, 운영 문서, ADR
- `wiki/`: 팀 내부 지식 기반
- `.github/`: GitHub template, workflow, automation 설정

`docs/`는 기능 문서나 산출물 문서에 사용하고, `wiki/`는 팀 내부 지식 기반으로 분리해서 관리합니다.

## Current Data Sources

- Official: Chanel Korea, Lush Korea, Lush UK, Jo Malone Korea, Granhand, Creed, Byredo, Le Labo, Nag Champa
- Fraganty: Bvlgari, Chanel, Dior
- Fragrantica: Giorgio Armani, Maison Francis Kurkdjian
- Retail exports: Tom Ford, Diptyque 계열 변환 유틸리티
