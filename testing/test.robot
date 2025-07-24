*** Variables ***

${HOSTNAME}             127.0.0.1
${PORT}                 8000
${SERVER}               http://${HOSTNAME}:${PORT}/
${BROWSER}              chrome
${MANAGE}               ../qcrbox_frontend/manage.py
${ADMIN_USERNAME}       admin
${ADMIN_PASSWORD}       admin
${USER_USERNAME}        user
${USER_PASSWORD}        user

*** Settings ***

Documentation   Django Robot Tests
Library         SeleniumLibrary  timeout=10  implicit_wait=0
Library         Process
Suite Setup     Start Django and open Browser
Suite Teardown  Stop Django and close Browser


*** Keywords ***
Start Django
  ${django process}=  Start process  python  ${MANAGE}  runserver
  Set suite variable  ${django process}

Stop Django
  Terminate Process  ${django process}

Start Django and open Browser
  Start Django
  Open Browser  ${SERVER}  ${BROWSER}

Stop Django and close browser
  Close All Browsers
  Stop Django
  
Log In As Admin
  Go To  ${SERVER}/login
  Page Should Contain Element  login-form
  Input Text  username  ${ADMIN_USERNAME}
  Input Text  password  ${ADMIN_PASSWORD}
  Click Button  submit-button
  
Log In As User
  Go To  ${SERVER}/login
  Page Should Contain Element  login-form
  Input Text  username  ${USER_USERNAME}
  Input Text  password  ${USER_PASSWORD}
  Click Button  submit-button

*** Test Cases ***

Scenario: As a visitor I should be redirected to a minimal login page
  Go To  ${SERVER}
  Page Should Contain Element  login-form
  Page Should Not Contain Element  home-link
  Page Should Not Contain Element  data-link
  Page Should Not Contain Element  groups-link
  Page Should Not Contain Element  users-link
  
Scenario: As a visitor I should be able to use the login form to log in
  Log In As Admin
  Wait Until Page Contains Element  message
  Page Should Not Contain   Login Failed
  Page Should Contain  Login Successful
