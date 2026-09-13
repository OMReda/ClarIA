# DIAGRAMMES PLANTUML — ClarIA (Plateforme Intelligente de Restitution)

> **Usage :** Copiez chaque bloc `@startuml ... @enduml` dans [PlantUML Online](https://plantuml.com/fr/) ou dans votre IDE (VS Code + extension PlantUML).
> Chaque diagramme correspond à la figure mentionnée dans le rapport.

---

## Figure 4 — Diagramme de Composants : Espace Utilisateur

```plantuml
@startuml Figure4_Composants_User
!theme plain
skinparam backgroundColor #FAFAFA
skinparam componentStyle rectangle
skinparam defaultFontName Inter

title Figure 4 — Diagramme de Composants\nEspace Utilisateur

package "Navigateur (React 18 + Vite)" {
  [LandingPage\n(statique, SSO redirect)] as LP_PAGE
  [UploadPage\n+ UploadZone] as UP
  [AskiPage\n+ PromptBar] as AP
  [DashboardPage\n+ react-grid-layout] as DP
  [ECharts Renderer] as EC
  [AG Grid] as AG
  [keycloak-js SDK] as KJS
  [SettingsPanel\n(config LLM via sessionStorage)] as SP
}

package "Backend FastAPI (Uvicorn/ASGI)" {
  [POST /api/v1/files\nGET /api/v1/files/{id}/data] as FR
  [POST /api/v1/files/{id}/prompts\nGET /api/v1/prompts/{id}\nPOST /api/v1/prompts/{id}/clarify] as PR
  [GET /api/v1/files/{id}/aggregate\nGET /api/v1/files/{id}/unique-values] as KR
  [GET /api/v1/health\nGET /api/v1/provider-status] as HL
  [file_validator\nlocale_normalizer] as FV
  [rate_limiter\n(Lua atomique Redis)] as RL
}

package "Celery Worker" {
  [process_prompt\n(8 étapes)] as CP
  [fuzzy_matcher] as FM
  [PandasAI\n+ DockerSandbox] as PAI
  [chart_resolver\n(8 types ECharts)] as CR
}

database "PostgreSQL" {
  [files\nprompts\ncharts] as DB
}

database "Redis" {
  [Broker Celery\n+ Pub/Sub WebSocket] as RD
}

cloud "Keycloak 26\nrealm: claria" {
  [claria-frontend\n(JWT RS256)] as KC
}

cloud "LLM" {
  [Ollama\n(qwen2.5-coder:7b)] as OL
  [Google / OpenAI\n/ Anthropic (fallback)] as CL
}

UP --> FR : "multipart/form-data"
UP --> AG : "preview_rows (10k)"
UP ..> HL : "GET /health (max_file_size_mb)"
AP --> PR : "POST prompt (Bearer JWT)"
AP ..> EC : "chart_spec JSON"
AP ..> SP : "lit sessionStorage\n(X-LLM-Provider / X-API-Key\nvia api/client.ts)"
DP --> KR : "GET aggregate\n(sum/avg/count/min/max)"
DP ..> HL : "GET /provider-status (polling 30s)"

FR --> FV : "validate + normalize"
PR --> RL : "check rate limit (30/h)"
PR --> RD : "delay(process_prompt)"
PR ..> RD : "WebSocket /ws/prompts/{id}"

CP --> FM : "extract_column_references"
CP --> PAI : "pai.DataFrame.chat()"
CP --> CR : "detect_chart_type\nbuild_chart_spec"
CP --> RD : "PUBLISH {chart_spec, status}"
CP --> DB : "UPDATE Prompt\nINSERT Chart"

FV --> DB : "INSERT files"
FR --> DB : "SELECT files"
PR --> DB : "INSERT Prompt"

KJS --> KC : "OAuth2 PKCE\nJWT RS256"
FR ..> KC : "JWKS validation (900s cache)"

LP_PAGE ..> KJS : "initKeycloak() au montage"

PAI --> OL : "inférence locale"
PAI ..> CL : "fallback cloud"

@enduml
```

---

## Figure 5 — Diagramme de Composants : Espace Administrateur

```plantuml
@startuml Figure5_Composants_Admin
!theme plain
skinparam backgroundColor #FAFAFA
skinparam componentStyle rectangle
skinparam defaultFontName Inter

title Figure 5 — Diagramme de Composants\nEspace Administrateur

package "Navigateur (React 18 + Vite)" {
  [AdminPage] as ADM
  [UserTable\n(list/create/edit/delete)] as UT
}

package "Backend FastAPI — Router admin" {
  [GET /platform-users/users] as LU
  [POST /platform-users/users] as CU
  [PUT /platform-users/users/{id}] as UU
  [DELETE /platform-users/users/{id}] as DU
  [PUT /platform-users/users/{id}/password] as PU
  [UserCreate validator\n(8+ chars, maj, min, chiffre, spécial)] as VAL
}

package "Service KeycloakAdminClient" {
  [get_token()\n(client_credentials + asyncio.Lock)] as GT
  [get_user() / list_users()\ncreate_user() / update_user()\ndelete_user() / set_password()\nlogout_user()] as KC_OPS
}

database "PostgreSQL" {
  [files → prompts → charts\n(CASCADE DELETE)] as PG
}

cloud "Stockage Physique\n/app/storage/{file_id}/" {
  [Fichiers CSV/Excel\n(shutil.rmtree)] as FS
}

cloud "Keycloak 26 Admin API\n/admin/realms/claria" {
  [users CRUD\n(bearer service token)] as KCA
}

ADM --> UT
UT --> LU : "GET (require_admin)"
UT --> CU : "POST (require_admin)"
UT --> UU : "PUT (require_admin)"
UT --> DU : "DELETE (require_admin)"
UT --> PU : "PUT /password (require_admin)"

CU --> VAL : "validate password complexity"
PU --> VAL : "validate password complexity"

LU --> GT : "service token"
CU --> GT
UU --> GT
DU --> GT
PU --> GT

GT --> KCA : "POST /token\n(client_credentials)"
LU ..> KC_OPS : "list_users()"
CU ..> KC_OPS : "create_user()"
UU ..> KC_OPS : "update_user()"
DU ..> KC_OPS : "delete_user() FIRST"
PU ..> KC_OPS : "set_password()"
KC_OPS --> KCA : "CRUD operations"

UU ..> KC_OPS : "logout_user()\nsi enabled=False"

DU --> PG : "DELETE charts\nDELETE prompts\nDELETE files"
DU --> FS : "shutil.rmtree(storage_path/{id})"

note right of DU
  Protection :
  - Auto-suppression interdite
    (user_id == admin.sub → 403)
  - Dernier non-admin protégé
    (last non-admin → 400)
end note

@enduml
```

---

## Figure 6 — Diagramme des Cas d'Utilisation : Acteur Utilisateur

```plantuml
@startuml Figure6_UseCase_User
!theme plain
skinparam backgroundColor #FAFAFA
skinparam defaultFontName Inter
left to right direction

title Figure 6 — Diagramme des Cas d'Utilisation\nActeur Utilisateur (rôle : user)

actor "Utilisateur\n(rôle : user)" as U

rectangle "ClarIA — Espace Utilisateur" {

  usecase "S'authentifier\n(Keycloak SSO)" as UC_AUTH
  usecase "Importer un fichier\n(CSV / Excel)" as UC_UPLOAD
  usecase "Valider le format\n(magic bytes, taille, encodage)" as UC_VALID
  usecase "Normaliser les données FR\n(nombres, dates)" as UC_NORM
  usecase "Sélectionner une feuille\n(Excel multi-feuilles)" as UC_SHEET
  usecase "Prévisualiser les données\n(AG Grid)" as UC_PREV
  usecase "Formuler une requête\nen langage naturel" as UC_PROMPT
  usecase "Classification d'intention\n(LLM / keywords)" as UC_CLASS
  usecase "Correspondance floue\ndes colonnes (fuzzy)" as UC_FUZZY
  usecase "Répondre à une question\nde clarification" as UC_CLARIF
  usecase "Visualiser le graphique\n(ECharts, WebSocket)" as UC_CHART
  usecase "Lire l'explication\n(synthèse FR automatique)" as UC_EXPL
  usecase "Épingler un graphique\nsur le tableau de bord" as UC_PIN
  usecase "Personnaliser le dashboard\n(drag-and-drop, resize)" as UC_DASH
  usecase "Ajouter un KPI\n(sum/avg/count/min/max)" as UC_KPI
  usecase "Choisir le fournisseur LLM\n(Ollama/OpenAI/Google)" as UC_LLM
  usecase "Supprimer un fichier" as UC_DEL

  UC_UPLOAD ..> UC_VALID : "<<include>>"
  UC_UPLOAD ..> UC_NORM : "<<include>>"
  UC_UPLOAD ..> UC_SHEET : "<<extend>>\n(si multi-feuilles)"
  UC_PROMPT ..> UC_CLASS : "<<include>>"
  UC_PROMPT ..> UC_FUZZY : "<<include>>"
  UC_FUZZY ..> UC_CLARIF : "<<extend>>\n(si ambiguïté colonne)"
  UC_CHART ..> UC_EXPL : "<<extend>>\n(si explain=true)"
}

U --> UC_AUTH
U --> UC_UPLOAD
U --> UC_PREV
U --> UC_PROMPT
U --> UC_CHART
U --> UC_PIN
U --> UC_DASH
U --> UC_KPI
U --> UC_LLM
U --> UC_DEL

UC_AUTH <.. UC_UPLOAD : "<<precondition>>"
UC_AUTH <.. UC_PROMPT : "<<precondition>>"
UC_AUTH <.. UC_DEL : "<<precondition>>"

@enduml
```

---

## Figure 7 — Diagramme des Cas d'Utilisation : Acteur Administrateur

```plantuml
@startuml Figure7_UseCase_Admin
!theme plain
skinparam backgroundColor #FAFAFA
skinparam defaultFontName Inter
left to right direction

title Figure 7 — Diagramme des Cas d'Utilisation\nActeur Administrateur (rôle : admin)

actor "Administrateur\n(rôle : admin)" as A

rectangle "ClarIA — Espace Administrateur" {

  usecase "S'authentifier\n(Keycloak SSO)" as UC_AUTH
  usecase "Lister tous les utilisateurs\n(Keycloak)" as UC_LIST
  usecase "Créer un utilisateur\n(+ validation mot de passe)" as UC_CREATE
  usecase "Modifier un utilisateur\n(nom, email, statut)" as UC_EDIT
  usecase "Désactiver un compte\n(logout forcé Keycloak)" as UC_DISABLE
  usecase "Réinitialiser le mot de passe\n(+ validation complexité)" as UC_RESET
  usecase "Supprimer un utilisateur\n(+ cascade DB + disque)" as UC_DELETE

  UC_EDIT ..> UC_DISABLE : "<<extend>>\n(si enabled=False)"

  note right of UC_DELETE
    Protections :
    - Impossible de se supprimer soi-même
      (user_id == admin.sub → 403)
    - Dernier non-admin protégé
      (len(non_admins) ≤ 1 → 400)
  end note

  note right of UC_EDIT
    Protections :
    - Le compte 'admin' ne peut être
      modifié que directement depuis
      la console native Keycloak (Realm claria).
      Modification bloquée dans l'app web.
  end note
}

A --> UC_AUTH
A --> UC_LIST
A --> UC_CREATE
A --> UC_EDIT
A --> UC_RESET
A --> UC_DELETE
UC_AUTH <.. UC_LIST : "<<precondition>>"
UC_AUTH <.. UC_CREATE : "<<precondition>>"

@enduml
```

---

## Figure 8 — Diagramme de Classes : Entités Métier

```plantuml
@startuml Figure8_Classes_Business
!theme plain
skinparam backgroundColor #FAFAFA
skinparam classAttributeIconSize 0
skinparam defaultFontName Inter

title Figure 8 — Diagramme de Classes\nEntités Métier (SQLAlchemy 2.0)

class "File" as FileModel {
  + id : UUID <<PK>>
  + owner_id : String(36) <<INDEX>>
  + original_filename : Text
  + file_type : String(10) <<CHECK: csv/xlsx/xls>>
  + size_bytes : Integer
  + row_count : Integer <<nullable>>
  + sheet_name : Text <<nullable>>
  + storage_path : Text
  + columns_metadata : JSON <<nullable>>
  + preview_rows : JSON <<nullable>>
  + dashboard_config : JSON <<nullable, ≤500Ko>>
  + status : String(30) <<CHECK>>
  + error_message : Text <<nullable>>
  + created_at : TIMESTAMPTZ
  --
  status IN ('uploaded','needs_sheet_selection',\n'validated','error')
}

class Prompt {
  + id : UUID <<PK>>
  + file_id : UUID <<FK→files(id) CASCADE>>
  + raw_text : Text
  + status : String(30) <<CHECK>>
  + clarification_question : Text <<nullable>>
  + clarification_answer : Text <<nullable>>
  + explanation : Text <<nullable>>
  + generated_code : Text <<nullable>>
  + error_message : Text <<nullable>>
  + created_at : TIMESTAMPTZ
  + completed_at : TIMESTAMPTZ <<nullable>>
  --
  status IN ('pending','processing',\n'awaiting_clarification','completed','failed')
}

class Chart {
  + id : UUID <<PK>>
  + prompt_id : UUID <<FK→prompts(id) CASCADE, UNIQUE>>
  + chart_type : String(20) <<CHECK>>
  + chart_spec : JSON
  + created_at : TIMESTAMPTZ
  --
  chart_type IN ('bar','line','pie','scatter',
  'histogram','area','radar','heatmap')
}

FileModel "1" *-- "0..*" Prompt : "owner_id / cascade delete"
Prompt "1" *-- "0..1" Chart : "prompt_id / cascade delete"

note right of FileModel
  Stockage physique :
  /app/storage/{file_id}/original.{ext}
  Nettoyage TTL : 7 jours (Celery Beat)
end note

note right of Chart
  chart_spec : spécification ECharts
  JSON native, rendu direct
  par ReactECharts
end note

@enduml
```

---

## Figure 9 — Diagramme de Classes : Couche Sécurité

```plantuml
@startuml Figure9_Classes_Security
!theme plain
skinparam backgroundColor #FAFAFA
skinparam classAttributeIconSize 0
skinparam defaultFontName Inter

title Figure 9 — Diagramme de Classes\nCouche Sécurité (JWT RS256 + RBAC)

class User {
  + sub : str
  + email : str
  + name : str
  + preferred_username : str
  + roles : List[str]
  --
  + is_admin : bool
}

class JWKSCache {
  - jwk_client : PyJWKClient
  - cache_ttl : int = 900s
  --
  + get_signing_key_from_jwt(token) : SigningKey
}

class TokenValidator {
  - keycloak_realm : str = "claria"
  - keycloak_client_id : str = "claria-frontend"
  - algorithms : List = ["RS256"]
  --
  + validate_issuer(iss : str) : bool
  + validate_azp(azp : str) : bool
  + extract_roles(payload : dict) : List[str]
  + auto_grant_user_role(roles : List) : List[str]
}

class KeycloakAdminClient {
  - server_url : str
  - realm : str = "claria"
  - client_id : str = "claria-admin"
  - client_secret : str
  - _cached_token : str
  - _token_expires_at : float
  - _token_lock : asyncio.Lock
  - _client : httpx.AsyncClient
  --
  + get_token() : str
  + get_user(user_id) : Dict
  + list_users() : List[Dict]
  + create_user(payload) : str
  + update_user(user_id, payload) : None
  + delete_user(user_id) : None
  + set_password(user_id, pwd) : None
  + logout_user(user_id) : None
}

class PasswordPolicy {
  --
  + validate(pwd: str) : str
  --
  min 8 caractères
  ≥1 majuscule, ≥1 minuscule
  ≥1 chiffre, ≥1 spécial
}

class FastAPIDependency <<interface>> {
  + get_current_user(token) : User
  + require_admin(user) : User
}

JWKSCache --> TokenValidator : "fournit clé publique"
TokenValidator --> User : "crée"
FastAPIDependency --> JWKSCache : "utilise"
FastAPIDependency --> TokenValidator : "utilise"
KeycloakAdminClient --> PasswordPolicy : "valide à la création\net au reset"

note right of TokenValidator
  validate_issuer() :
  iss.endswith("/realms/claria")
  (hostname-agnostic)
end note

note right of KeycloakAdminClient
  Double-checked locking :
  asyncio.Lock évite les
  token refresh concurrents
end note

@enduml
```

---

## Figure 10 — Diagramme de Séquence : Pipeline Complet

```plantuml
@startuml Figure10_Sequence_Pipeline
!theme plain
skinparam backgroundColor #FAFAFA
skinparam defaultFontName Inter
skinparam sequenceArrowThickness 1.5

title Figure 10 — Diagramme de Séquence\nPipeline Complet Upload → Aski → WebSocket → ECharts

actor "Utilisateur" as U
participant "React Frontend" as FE
participant "FastAPI" as API
participant "Redis" as RD
participant "Celery Worker" as CW
participant "PandasAI" as PAI
participant "Ollama / LLM" as LLM
database "PostgreSQL" as PG

== Phase 1 : Import du fichier ==

U -> FE : Sélectionne fichier (≤10 Mo, CSV/Excel)
FE -> FE : validateFile() — vérif taille + extension (INSTANT)
FE -> API : POST /api/v1/files (multipart, Bearer JWT)
API -> API : detect_content_type() — magic bytes
API -> API : save_upload() — /storage/{file_id}/original.ext
API -> API : read_csv_safe() / read_excel_safe()
API -> API : build_columns_metadata() + build_preview_rows()
API -> PG : INSERT files (status='validated')
API --> FE : 201 {file_id, columns, preview_rows}
FE -> FE : AG Grid — affichage prévisualisation

== Phase 2 : Soumission du prompt ==

U -> FE : Saisit question en langage naturel
FE -> API : POST /api/v1/files/{id}/prompts\n(Bearer JWT, X-LLM-Provider, X-Explain)
API -> API : check_and_increment() — rate limit (30/h, Lua atomique)
API -> PG : INSERT Prompt (status='pending')
API -> RD : delay(process_prompt, prompt_id, llm_config)
API --> FE : 202 {prompt_id}
FE -> API : WS /ws/prompts/{prompt_id}?token=JWT
API --> FE : WebSocket CONNECTED

== Phase 3 : Pipeline IA (Celery) ==

RD -> CW : Dépile tâche
CW -> PG : UPDATE Prompt (status='processing')
CW -> RD : PUBLISH {status:'processing', message:'Analysing...'}
FE <-- RD : WS message → affiche spinner

CW -> CW : configure_pandasai(llm_config)\n→ Ollama ou fallback cloud

CW -> LLM : classify_data_intent()\n(cloud uniquement — keywords si local)
LLM --> CW : YES / NO
note right : Si NO → status='failed'\nmessage d'aide en FR

CW -> CW : fuzzy_matcher — extract_column_references()
note right : HIGH ≥80% → correction silencieuse\nMID 50-79% → awaiting_clarification\nLOW <50% → awaiting_clarification

CW -> CW : detect_chart_type() → 8 types\n+ build_aggregation_prompt(chart_type)
note right : detect_chart_type() est AVANT PandasAI\npour construire le bon engineered_prompt

CW -> PAI : pai.DataFrame.chat(engineered_prompt, sandbox)
PAI -> LLM : Code Python + exécution sandboxée
LLM --> PAI : DataFrame agrégé
PAI --> CW : result_df + generated_code

CW -> CW : build_chart_spec(result_df, auto_pivot)

CW -> PG : INSERT Chart (chart_type, chart_spec)
CW -> PG : UPDATE Prompt (status='completed', completed_at)

opt explain=true
  CW -> LLM : generate_explanation() → 1-2 phrases FR
  LLM --> CW : explication textuelle
  CW -> PG : UPDATE Prompt (explanation)
end

CW -> RD : PUBLISH {status:'completed', chart:{...}, explanation}
FE <-- RD : WS message
FE -> FE : ReactECharts.render(chart_spec)
U <-- FE : Graphique interactif + explication

@enduml
```

---

## Figure 11 — Diagramme de Séquence : Authentification Keycloak

```plantuml
@startuml Figure11_Sequence_Auth
!theme plain
skinparam backgroundColor #FAFAFA
skinparam defaultFontName Inter
skinparam sequenceArrowThickness 1.5

title Figure 11 — Diagramme de Séquence\nAuthentification Keycloak JWT RS256

actor "Utilisateur" as U
participant "React\n(keycloak-js 26)" as FE
participant "Keycloak 26\n(realm: claria)" as KC
participant "FastAPI\n(security.py)" as API
participant "JWKS Cache\n(TTL 900s)" as JWKS

== Authentification initiale ==

U -> FE : Accède à ClarIA
FE -> KC : Initiation OAuth2 PKCE\n(client_id=claria-frontend)
KC --> U : Redirection page de login
U -> KC : Saisit username + password
KC --> FE : JWT RS256 (access_token + refresh_token)
FE -> FE : Stocke token en mémoire\n(jamais localStorage)

== Requête API authentifiée ==

FE -> API : GET /api/v1/files\nAuthorization: Bearer <JWT>

API -> JWKS : get_signing_key_from_jwt(token)
alt Cache valide (< 900s)
  JWKS --> API : clé publique (cache hit)
else Cache expiré
  JWKS -> KC : GET /realms/claria/protocol/openid-connect/certs
  KC --> JWKS : JWKS (clés publiques RS256)
  JWKS --> API : clé publique (cache miss — rafraîchi)
end

API -> API : jwt.decode(token, signing_key, RS256)
API -> API : validate_issuer(iss.endswith("/realms/claria"))
API -> API : validate_azp(azp == "claria-frontend")
API -> API : extract_roles(realm_access.roles)

alt Aucun rôle détecté
  API -> API : auto_grant ["user"]
end

API --> FE : 200 (données autorisées)

== Rafraîchissement automatique ==

FE -> FE : Token expire dans < 30s ?
FE -> KC : POST /token (grant_type=refresh_token)
KC --> FE : Nouveau JWT RS256
note right of FE : Transparent pour l'utilisateur

@enduml
```

---

## Figure 12 — Diagramme d'Activité : Validation d'un Fichier

```plantuml
@startuml Figure12_Activity_FileValidation
!theme plain
skinparam backgroundColor #FAFAFA
skinparam defaultFontName Inter
skinparam activityFontSize 12

title Figure 12 — Diagramme d'Activité\nValidation et Normalisation d'un Fichier CSV/Excel

start

:Réception fichier (multipart/form-data);
:Lecture raw_bytes;

note right
  check_file_size() d'abord (files.py L96)
  puis vérification vide (files.py L100)
end note

if (file.size ≤ MAX_FILE_SIZE_MB (10 Mo) ?) then (non)
  :HTTP 400 FILE_TOO_LARGE;
  stop
endif

if (file.size > 0 ?) then (non)
  :HTTP 400 EMPTY_FILE;
  stop
endif

note right
  Validation frontend (instantanée)
  ET validation backend (magic bytes)
end note

:detect_content_type(raw_bytes[:2048]);

if (Extension et magic bytes cohérents ?\n(csv / xlsx / xls)) then (non)
  :HTTP 400 INVALID_FILE_TYPE;
  stop
endif

:save_upload() → /storage/{file_id}/original.ext;

if (Fichier Excel ?) then (oui)
  :read_excel_safe(raw_bytes, sheet_name=None);
  if (Plusieurs feuilles ET DataFrame vide ?) then (oui)
    :INSERT File (status='needs_sheet_selection');
    :Retourner {status, sheet_names};
    stop
  else (non)
    :Charger la première feuille;
  endif
else (non, CSV)
  :chardet.detect(raw_bytes) → encodage;
  :read_csv_safe(raw_bytes, encoding);
endif

:locale_normalizer — nombres FR (1 234,56 → 1234.56);
:locale_normalizer — dates FR (dd/mm/yyyy → ISO 8601);

if (len(df) > MAX_ROWS (100 000) ?) then (oui)
  :HTTP 400 TOO_MANY_ROWS;
  stop
endif

:build_columns_metadata(df)\n(name, dtype, missing_count);
:build_preview_rows(df, n=5);

:INSERT File (status='validated');

:HTTP 201 {file_id, status, columns, preview_rows, row_count};

stop

@enduml
```

---

## Figure 13 — Diagramme d'Activité : Suppression en Cascade (Admin)

```plantuml
@startuml Figure13_Activity_CascadeDelete
!theme plain
skinparam backgroundColor #FAFAFA
skinparam defaultFontName Inter
skinparam activityFontSize 12

title Figure 13 — Diagramme d'Activité\nSuppression en Cascade d'un Utilisateur (Administrateur)

start

:DELETE /api/v1/platform-users/users/{user_id};
:require_admin() — validation JWT;

if (L'appelant (requester) est admin ?) then (non)
  :HTTP 403 FORBIDDEN;
  stop
endif

if (user_id == admin.sub ?) then (oui)
  :HTTP 403 CANNOT_DELETE_SELF;
  stop
endif

:kc_client.list_users();
:Filtrer non-admins\n(username != 'adminuser'/'admin');

if (len(non_admins) ≤ 1\nET user_id dans non_admins ?) then (oui)
  :HTTP 400 LAST_USER_PROTECTED;
  stop
endif

:SELECT files WHERE owner_id = user_id;

:kc_client.delete_user(user_id)\n← Keycloak PRIORITAIRE;

if (Erreur Keycloak ?) then (oui)
  :Lever exception — DB non modifiée;
  stop
endif

if (file_ids non vides ?) then (oui)
  :SELECT Prompt.id WHERE file_id IN [file_ids];
  :DELETE Chart WHERE prompt_id IN [prompt_ids];
  :DELETE Prompt WHERE file_id IN [file_ids];
  :DELETE File WHERE id IN [file_ids];
  :db.commit();
  :shutil.rmtree(/storage/{file_id}) pour chaque file;
endif

:HTTP 204 No Content;
stop

@enduml
```

---

## Figure 14 — Diagramme d'État : Cycle de Vie des Entités

```plantuml
@startuml Figure14_State_FilePrompt
!theme plain
skinparam backgroundColor #FAFAFA
skinparam defaultFontName Inter
skinparam stateFontSize 12

title Figure 14 — Diagramme d'État\nCycles de vie : File.status et Prompt.status

state "File.status" as FS {
  state "uploaded" as F_UP
  state "needs_sheet_selection" as F_NSS
  state "validated" as F_VAL
  state "error" as F_ERR

  [*] --> F_UP : INSERT (upload reçu)
  F_UP --> F_NSS : Excel multi-feuilles détecté
  F_UP --> F_VAL : CSV ou Excel mono-feuille OK
  F_NSS --> F_VAL : POST /sheet — feuille sélectionnée
  F_UP --> F_ERR : Erreur validation / normalisation
  F_VAL --> [*] : DELETE ou TTL 7j expiré
  F_ERR --> [*] : Suppression manuelle
}

state "Prompt.status" as PS {
  state "pending" as P_PEND
  state "processing" as P_PROC
  state "awaiting_clarification" as P_AWAIT
  state "completed" as P_COMP
  state "failed" as P_FAIL

  [*] --> P_PEND : POST /prompts (INSERT)
  P_PEND --> P_PROC : Celery task démarre
  P_PROC --> P_AWAIT : fuzzy_matcher — ambiguïté colonne\n(score 50-79% ou <50%)
  P_AWAIT --> P_PEND : POST /clarify — réponse reçue
  P_PROC --> P_COMP : Pipeline complet (chart_spec généré)
  P_PROC --> P_FAIL : Erreur LLM / timeout / intention non-data
  P_COMP --> [*]
  P_FAIL --> [*]
}

note "File.status = 'validated'\nest requis pour soumettre\nun Prompt sur ce fichier." as N1

@enduml
```

---

## Figure 15 — Modèle Conceptuel de Données (MCD/ERD)

```plantuml
@startuml Figure15_MCD
!theme plain
skinparam backgroundColor #FAFAFA
skinparam defaultFontName Inter

title Figure 15 — Modèle Conceptuel de Données (MCD)\nClarIA — Entités File, Prompt, Chart

entity "FILE" as F {
  * id : UUID <<PK>>
  --
  * owner_id : String <<Keycloak sub>>
  * original_filename : Text
  * file_type : Enum(csv/xlsx/xls)
  * size_bytes : Integer
  o row_count : Integer
  o sheet_name : Text
  * storage_path : Text
  o columns_metadata : JSON
  o preview_rows : JSON
  o dashboard_config : JSON <<≤500Ko>>
  * status : Enum(4 états)
  o error_message : Text
  * created_at : TIMESTAMPTZ
}

entity "PROMPT" as P {
  * id : UUID <<PK>>
  --
  * file_id : UUID <<FK>>
  * raw_text : Text
  * status : Enum(5 états)
  o clarification_question : Text
  o clarification_answer : Text
  o explanation : Text
  o generated_code : Text
  o error_message : Text
  * created_at : TIMESTAMPTZ
  o completed_at : TIMESTAMPTZ
}

entity "CHART" as C {
  * id : UUID <<PK>>
  --
  * prompt_id : UUID <<FK, UNIQUE>>
  * chart_type : Enum(8 types)
  * chart_spec : JSON
  * created_at : TIMESTAMPTZ
}

F ||--o{ P : "FILE possède\n0..N PROMPT"
P ||--o| C : "PROMPT génère\n0..1 CHART"

note right of F
  * = obligatoire / o = optionnel
  CASCADE DELETE :
  FILE → PROMPT → CHART
end note

note right of C
  chart_type :
  bar, line, area, pie, scatter,
  histogram, radar, heatmap
  (8 types — migration 3f8c1a2b)
end note

@enduml
```

---

## Figure 16 — Diagramme de Déploiement : Infrastructure Docker

```plantuml
@startuml Figure16_Deployment
!theme plain
skinparam backgroundColor #FAFAFA
skinparam defaultFontName Inter
skinparam nodeStyle rectangle

title Figure 16 — Diagramme de Déploiement\nInfrastructure Docker Compose — ClarIA

node "Serveur Docker Compose" {

  node "frontend — nginx:alpine :80\n(1 seul conteneur Docker)" as FE_NODE {
    [React 18 SPA\n(build Vite 5 — artefact statique)]
    [Nginx Reverse Proxy\n/api/ + /ws/* → :8000\n/* → fichiers statiques React]
  }

  node "Python 3.11 / Uvicorn :8000" as BE_NODE {
    [FastAPI\n5 routeurs + health + provider-status]
    [file_validator · locale_normalizer\nkeycloak_admin · rate_limiter]
  }

  node "Python 3.11 / Celery (worker)" as CW_NODE {
    [process_prompt\n(pipeline IA 8 étapes)]
    [cleanup_expired_files\n(Celery Beat, TTL 7j)]
  }

  node "redis:7-alpine :6379" as RD_NODE {
    [Broker Celery]
    [Pub/Sub WebSocket]
    [Rate Limiter Lua]
  }

  node "postgres:16-alpine :5432" as PG_NODE {
    database "plateforme" {
      [files · prompts · charts]
    }
  }

  node "keycloak:26 :8080" as KC_NODE {
    [Realm: claria\nclaria-frontend + claria-admin]
  }

  node "ollama/ollama :11434" as OL_NODE {
    [qwen2.5-coder:7b]
  }

  node "Alembic (migrate)" as MIG {
    [upgrade head\n4 révisions → avant backend]
  }
}

FE_NODE ..> BE_NODE : "HTTP JWT + /api/ + /ws/"
FE_NODE ..> KC_NODE : "OAuth2 PKCE\n+ /realms/ proxy"
BE_NODE --> RD_NODE : "Celery + Pub/Sub"
BE_NODE --> PG_NODE : "asyncpg"
BE_NODE --> KC_NODE : "JWKS + Admin API"
CW_NODE --> RD_NODE : "broker + PUBLISH"
CW_NODE --> PG_NODE : "psycopg2"
CW_NODE --> OL_NODE : "POST /api/generate"
MIG --> PG_NODE : "DDL"

cloud "Cloud LLM (fallback optionnel)" {
  [Google Gemini\nOpenAI GPT-4o-mini\nAnthropic Claude]
}

CW_NODE ..> "Cloud LLM (fallback optionnel)" : "Si Ollama offline"

@enduml
```

---

## Figure 17 — Diagramme de Gantt : Planning Projet

```plantuml
@startuml Figure17_Gantt
!theme plain
skinparam backgroundColor #FAFAFA
skinparam defaultFontName Inter

title Figure 17 — Diagramme de Gantt\nClarIA — Phase de Développement & Rédaction (Juillet - Août 2026)\nOUSSAMA MOHAMED REDA

project starts 2026-07-01

-- Phase 1 — Cadrage & Recherche (S1) --
[Rédaction CDC (Cahier des Charges)] lasts 7 days
[Rédaction CDC (Cahier des Charges)] starts 2026-07-01

[Recherche bibliographique & état de l'art] lasts 10 days
[Recherche bibliographique & état de l'art] starts 2026-07-01

[Analyse des besoins métier SKATYS] lasts 8 days
[Analyse des besoins métier SKATYS] starts 2026-07-05

-- Phase 2 — Conception (S2) --
[Architecture système (FastAPI, React, Celery, Redis)] lasts 7 days
[Architecture système (FastAPI, React, Celery, Redis)] starts 2026-07-08

[Modélisation UML — 14 diagrammes] lasts 11 days
[Modélisation UML — 14 diagrammes] starts 2026-07-08

[Modélisation BDD — schéma File / Prompt / Chart] lasts 5 days
[Modélisation BDD — schéma File / Prompt / Chart] starts 2026-07-14

-- Phase 3 — Développement Backend & IA (S3) --
[FastAPI + Auth JWT (Keycloak 26, RS256, RBAC)] lasts 9 days
[FastAPI + Auth JWT (Keycloak 26, RS256, RBAC)] starts 2026-07-13

[Pipeline IA (PandasAI, LiteLLM, fuzzy matcher)] lasts 10 days
[Pipeline IA (PandasAI, LiteLLM, fuzzy matcher)] starts 2026-07-16

[Celery + Redis async (WebSocket, rate limiter Lua)] lasts 9 days
[Celery + Redis async (WebSocket, rate limiter Lua)] starts 2026-07-18

-- Phase 4 — Frontend & Tests (S4) --
[Interface React (UploadZone, AskiPage, Dashboard)] lasts 10 days
[Interface React (UploadZone, AskiPage, Dashboard)] starts 2026-07-20

[Tests Pytest — 40 tests, couverture 100%] lasts 8 days
[Tests Pytest — 40 tests, couverture 100%] starts 2026-07-24

[Correction bugs & optimisation] lasts 6 days
[Correction bugs & optimisation] starts 2026-07-26

-- Phase 5 — Rédaction & Finalisation --
[Rédaction du Rapport PFA & Documentation] lasts 25 days
[Rédaction du Rapport PFA & Documentation] starts 2026-07-25

' ——— Couleurs par phase ———
[Rédaction CDC (Cahier des Charges)] is colored in CornflowerBlue/White
[Recherche bibliographique & état de l'art] is colored in CornflowerBlue/White
[Analyse des besoins métier SKATYS] is colored in CornflowerBlue/White

[Architecture système (FastAPI, React, Celery, Redis)] is colored in MediumSlateBlue/White
[Modélisation UML — 14 diagrammes] is colored in MediumSlateBlue/White
[Modélisation BDD — schéma File / Prompt / Chart] is colored in MediumSlateBlue/White

[FastAPI + Auth JWT (Keycloak 26, RS256, RBAC)] is colored in SeaGreen/White
[Pipeline IA (PandasAI, LiteLLM, fuzzy matcher)] is colored in SeaGreen/White
[Celery + Redis async (WebSocket, rate limiter Lua)] is colored in SeaGreen/White

[Interface React (UploadZone, AskiPage, Dashboard)] is colored in DarkOrange/White
[Tests Pytest — 40 tests, couverture 100%] is colored in DarkOrange/White
[Correction bugs & optimisation] is colored in DarkOrange/White

[Rédaction du Rapport PFA & Documentation] is colored in Crimson/White

note bottom
  **Soutenance Finale** : Date exacte à confirmer (prévue courant Septembre 2026).
end note

@enduml
```

---

## Récapitulatif des Figures

| Figure | Type | Section rapport | Acteur principal |
|---|---|---|---|
| **Figure 4** | Composants | 3.2.2 | Utilisateur |
| **Figure 5** | Composants | 3.2.3 | Administrateur |
| **Figure 6** | Cas d'utilisation | 3.3.1 | Utilisateur |
| **Figure 7** | Cas d'utilisation | 3.3.2 | Administrateur |
| **Figure 8** | Classes (métier) | 3.4.1 | — |
| **Figure 9** | Classes (sécurité) | 3.4.2 | — |
| **Figure 10** | Séquence pipeline | 3.5.1 | Utilisateur |
| **Figure 11** | Séquence auth | 3.5.2 | — |
| **Figure 12** | Activité validation | 3.6.1 | Utilisateur |
| **Figure 13** | Activité suppression | 3.6.2 | Administrateur |
| **Figure 14** | États | 3.6.3 | — |
| **Figure 15** | MCD / ERD | 3.4.3 | — |
| **Figure 16** | Déploiement | 3.7 | — |
| **Figure 17** | Gantt | 3.8 | — |
