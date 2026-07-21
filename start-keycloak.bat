@echo off
echo Starting Keycloak in DEV mode...

set KC_BOOTSTRAP_ADMIN_USERNAME=admin
set KC_BOOTSTRAP_ADMIN_PASSWORD=CqKiAA2CEdMWXLixQfWN3kkqVjmw72D_

:: Note: To cleanly re-import the realm configuration, copy infra\keycloak\claria-realm.json 
:: to infra\keycloak\keycloak-26.7.0\data\import\ and start this script with the --import-realm flag:
:: start-keycloak.bat --import-realm

cd infra\keycloak\keycloak-26.7.0\bin
kc.bat start-dev %*
