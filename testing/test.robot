*** Variables ***

${HOSTNAME}             127.0.0.1
${PORT}                 8000
${SERVER}               http://${HOSTNAME}:${PORT}/
${BROWSER}              chrome
${MANAGE}               ../qcrbox_frontend/manage.py
${ROBOT_PREFIX}         _ROBOT_
${ADMIN_USERNAME}       ${ROBOT_PREFIX}admin
${ADMIN_PASSWORD}       test_pass_0123
${USER_USERNAME}        ${ROBOT_PREFIX}user
${USER_PASSWORD}        test_pass_0123

*** Settings ***

Documentation   Django Robot Tests
Library         SeleniumLibrary  timeout=10  implicit_wait=0
Library         Process
Suite Setup     Start Django and open Browser
Suite Teardown  Stop Django and close Browser


*** Keywords ***
Start Django and open Browser
  Start Django
  Open Browser  ${SERVER}  ${BROWSER}

Stop Django and close browser
  Close All Browsers
  Stop Django
  
Start Django
  Create Initial Data
  ${django process}=  Start process  python  ${MANAGE}  runserver
  Set suite variable  ${django process}

Stop Django
  Cleanup Initial Data
  Terminate Process  ${django process}
  
Create Initial Data
  Create Test Admin
  Create Test User
  
Cleanup Initial Data
  Cleanup Test Data
  
Create Test Admin
  Start process  python  ${MANAGE}  create_robot_user  ${ADMIN_USERNAME}  dummy@email.com  ${ADMIN_PASSWORD}  admin

Create Test User
  Start process  python  ${MANAGE}  create_robot_user  ${USER_USERNAME}  dummy@email.com  ${USER_PASSWORD}  user

Cleanup Test Data
  Start process  python  ${MANAGE}  cleanup_robot_data

Add Group
  [Arguments]  ${group_name}
  Go To  ${SERVER}/view_groups
  Wait Until Page Contains Element  display-table
  Click Button  create-new-button
  Wait Until Page Contains Element  create-form
  Input Text  name  ${group_name}
  Click Button  submit-button
  Wait Until Page Contains Element  message
  
Add User
  [Arguments]  ${username}  ${group_name}
  Go To  ${SERVER}/view_users
  Wait Until Page Contains Element  display-table
  Click Button  create-new-button
  Wait Until Page Contains Element  create-form
  Input Text  username  ${username}
  Input Text  password1  ${USER_PASSWORD}
  Input Text  password2  ${USER_PASSWORD}
  Input Text  email  dummy@email.com
  Input Text  first_name  first_name
  Input Text  last_name  last_name
  Select From List By Label  user_groups  ${group_name}
  Click Button  submit-button
  Wait Until Page Contains Element  message
  
Log In As Admin
  Go To  ${SERVER}/login
  Page Should Contain Element  login-form
  Input Text  username  ${ADMIN_USERNAME}
  Input Text  password  ${ADMIN_PASSWORD}
  Click Button  submit-button
  Wait Until Page Contains Element  message
  
Log In As User
  Go To  ${SERVER}/login
  Page Should Contain Element  login-form
  Input Text  username  ${USER_USERNAME}
  Input Text  password  ${USER_PASSWORD}
  Click Button  submit-button
  Wait Until Page Contains Element  message

Log Out
  Go To  ${SERVER}/logout
  Wait Until Page Contains Element  message

*** Test Cases ***

As a Visitor: I should be redirected to a minimal login page
  Go To  ${SERVER}
  Page Should Contain Element  login-form
  Page Should Not Contain Element  home-link
  Page Should Not Contain Element  data-link
  Page Should Not Contain Element  groups-link
  Page Should Not Contain Element  users-link
  
I should be able to use the login form to log in
  Log In As User
  Page Should Not Contain   Login Failed
  Page Should Contain  Login Successful
  
As a User: I should be able to log out
  Log Out
  Page Should Contain  Logout Successful
  
I should be able to edit my account details
  Log In As User
  Go To  ${SERVER}/edit_account
  Wait Until Page Contains Element  edit-form
  Input Text  first_name  test first name
  Input Text  last_name  test last name
  Input Text  email  test@email.com
  Click Button  submit-button
  Wait Until Page Contains Element  message
  Page Should Contain  Account updated successfully
  Go To  ${SERVER}/edit_account
  Element Attribute Value Should Be  first_name  value  test first name
  Element Attribute Value Should Be  last_name  value  test last name
  Element Attribute Value Should Be  email  value  test@email.com
  
I should be able to change my password
  Go To  ${SERVER}/edit_password
  Wait Until Page Contains Element  edit-form
  Input Text  old_password  ${USER_PASSWORD}
  Input Text  new_password1  ${USER_PASSWORD}_edited123
  Input Text  new_password2  ${USER_PASSWORD}_edited123
  Click Button  submit-button
  Wait Until Page Contains Element  message
  Page Should Contain  Password updated successfully
  Log Out
  Go To  ${SERVER}/login
  Page Should Contain Element  login-form
  Input Text  username  ${USER_USERNAME}
  Input Text  password  ${USER_PASSWORD}_edited123
  Click Button  submit-button
  Wait Until Page Contains Element  message
  Page Should Not Contain   Login Failed
  Page Should Contain  Login Successful
  
As an Admin: I should be able to create new groups
  Log Out
  Log In As Admin
  Go To  ${SERVER}/view_groups
  Wait Until Page Contains Element  display-table
  Element Should Not Contain  display-table  ${ROBOT_PREFIX}grouptest  
  Add Group  ${ROBOT_PREFIX}grouptest
  Page Should Contain  New Group "${ROBOT_PREFIX}grouptest" added
  Go To  ${SERVER}/view_groups
  Wait Until Page Contains Element  display-table
  Element Should Contain  display-table  ${ROBOT_PREFIX}grouptest
  
I should be able to edit groups
  Go To  ${SERVER}/view_groups
  Wait Until Page Contains Element  display-table
  Click Link  edit-link-${ROBOT_PREFIX}grouptest
  Wait Until Page Contains Element  edit-form
  Input Text  name  ${ROBOT_PREFIX}edited
  Click Button  submit-button
  Wait Until Page Contains Element  message
  Page Should Contain  Changes to "${ROBOT_PREFIX}edited" saved!
  Go To  ${SERVER}/view_groups
  Wait Until Page Contains Element  display-table
  Element Should Contain  display-table  ${ROBOT_PREFIX}edited
  Element Should Not Contain  display-table  ${ROBOT_PREFIX}grouptest
  
I should be able to delete groups
  Go To  ${SERVER}/view_groups
  Wait Until Page Contains Element  display-table
  Click Link  delete-link-${ROBOT_PREFIX}edited
  Handle Alert  ACCEPT
  Wait Until Page Contains Element  display-table
  Element Should Not Contain  display-table  ${ROBOT_PREFIX}edited

I should be able to create a new user
  Add Group  ${ROBOT_PREFIX}1
  Add Group  ${ROBOT_PREFIX}2
  Go To  ${SERVER}/view_users
  Wait Until Page Contains Element  display-table
  Element Should Not Contain  display-table  ${ROBOT_PREFIX}usertest  
  Add User  ${ROBOT_PREFIX}usertest  ${ROBOT_PREFIX}1
  Page Should Contain  Registration Successful
  Go To  ${SERVER}/view_users
  Wait Until Page Contains Element  display-table
  Element Should Contain  display-table  ${ROBOT_PREFIX}usertest
  Element Should Contain  cell-Group(s)-${ROBOT_PREFIX}usertest  ${ROBOT_PREFIX}1
  Element Should Not Contain  cell-Group(s)-${ROBOT_PREFIX}usertest  ${ROBOT_PREFIX}2
  
I should be able to edit a user
  Go To  ${SERVER}/view_users
  Wait Until Page Contains Element  display-table
  Click Link  edit-link-${ROBOT_PREFIX}usertest
