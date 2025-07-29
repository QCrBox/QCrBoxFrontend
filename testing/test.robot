*** Variables ***

${HOSTNAME}             127.0.0.1
${PORT}                 8000
${SERVER}               http://${HOSTNAME}:${PORT}
${MANAGE}               ../qcrbox_frontend/manage.py
${ROBOT_PREFIX}         _ROBOT_

${USERNAME}        ${ROBOT_PREFIX}user
${PASSWORD}        test_pass_0123
${GROUP}           ${ROBOT_PREFIX}group
${TEST_FILENAME}   robot_test.cif
${TEST_FILEPATH}   ${CURDIR}/${TEST_FILENAME}
${DOWNLOAD_DIR}    ${CURDIR}/download

*** Settings ***

Documentation   Django Robot Tests
Library         SeleniumLibrary  timeout=100  implicit_wait=0
Library         OperatingSystem
Library         Process
Suite Setup     Clean Up and Start
Suite Teardown  Stop Django and close Browser


*** Keywords ***
Clean Up and Start
  Remove File  ${CURDIR}/*.png
  Start Django and open Browser

Start Django and open Browser
  Start Django
  VAR  &{browser_prefs}  download.default_directory=${DOWNLOAD_DIR}
  ${chrome_options}  Evaluate  sys.modules['selenium.webdriver'].ChromeOptions()  sys, selenium.webdriver
  Call Method  ${chrome_options}  add_experimental_option  prefs  ${browser_prefs}
  Open Browser  ${SERVER}  chrome  options=${chrome_options}
  Maximize Browser Window

Stop Django and close browser
  Close All Browsers
  Stop Django

Start Django
  Create Initial Data
  ${django process}=  Start process  python  ${MANAGE}  runserver
  Set suite variable  ${django process}

Stop Django
  Cleanup Test Data
  Terminate Process  ${django process}
  
Create Initial Data
  Create Test Users

Create Test Users
  Start process  python  ${MANAGE}  create_robot_user  ${USERNAME}1  dummy@email.com  ${PASSWORD}  global manager
  Start process  python  ${MANAGE}  create_robot_user  ${USERNAME}2  dummy@email.com  ${PASSWORD}  group manager
  Start process  python  ${MANAGE}  create_robot_user  ${USERNAME}3  dummy@email.com  ${PASSWORD}  user

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
  Input Text  password1  ${PASSWORD}
  Input Text  password2  ${PASSWORD}
  Input Text  email  dummy@email.com
  Input Text  first_name  first_name
  Input Text  last_name  last_name
  Select From List By Label  user_groups  ${group_name}
  Click Button  submit-button
  Wait Until Page Contains Element  message
  
Add Group to User
  [Arguments]  ${username}  ${group_name}
  Go To  ${SERVER}/view_users
  Wait Until Page Contains Element  display-table
  Click Link  edit-link-${username}
  Wait Until Page Contains Element  edit-form
  Select From List By Label  groups  ${group_name}
  Click Button  submit-button
  Wait Until Page Contains Element  message

Log In As
  [Arguments]  ${username}  ${password}
  Go To  ${SERVER}/login
  Page Should Contain Element  login-form
  Input Text  username  ${username}
  Input Text  password  ${password}
  Click Button  submit-button
  Wait Until Page Contains Element  message
  
Log In As User
  [Arguments]  ${user_id}
  Log In As  ${USERNAME}${user_id}  ${PASSWORD}

Log Out
  Go To  ${SERVER}/logout
  Wait Until Page Contains Element  message
  
Upload Copied File
  [Arguments]  ${filename}  ${group_name}
  Go To  ${SERVER}/workflow
  Copy File  ${TEST_FILEPATH}  ${CURDIR}/${filename}
  Select From List By Label  group  ${group_name}
  Choose File  upload-dataset-file  ${CURDIR}/${filename}
  Click Button  upload-button
  Wait Until Page Contains Element  workflow-display
  Remove File  ${CURDIR}/${filename}

*** Test Cases ***

As a Visitor: I should be redirected to a minimal login page
  Go To  ${SERVER}
  Page Should Contain Element  login-form
  Page Should Not Contain Element  home-link
  Page Should Not Contain Element  data-link
  Page Should Not Contain Element  groups-link
  Page Should Not Contain Element  users-link
  
As a Visitor: I should be able to use the login form to log in
  Log In As User  3
  Page Should Not Contain  Login Failed
  Page Should Contain  Login Successful

As Any User: I should be able to log out
  Log Out
  Page Should Contain  Logout Successful
  
As Any User: I should be able to edit my account details
  Log In As User  3
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
  
As Any User: I should be able to change my password
  Go To  ${SERVER}/edit_password
  Wait Until Page Contains Element  edit-form
  Input Text  old_password  ${PASSWORD}
  Input Text  new_password1  ${PASSWORD}_edited
  Input Text  new_password2  ${PASSWORD}_edited
  Click Button  submit-button
  Wait Until Page Contains Element  message
  Page Should Contain  Password updated successfully
  Log Out
  Go To  ${SERVER}/login
  Page Should Contain Element  login-form
  Input Text  username  ${USERNAME}3
  Input Text  password  ${PASSWORD}_edited
  Click Button  submit-button
  Wait Until Page Contains Element  message
  Page Should Not Contain  Login Failed
  Page Should Contain  Login Successful
  Go To  ${SERVER}/edit_password
  Wait Until Page Contains Element  edit-form
  Input Text  old_password  ${PASSWORD}_edited
  Input Text  new_password1  ${PASSWORD}
  Input Text  new_password2  ${PASSWORD}
  Click Button  submit-button
  Wait Until Page Contains Element  message
  
As a Global Manager: I should be able to create new groups
  Log Out
  Log In As User  1
  Go To  ${SERVER}/view_groups
  Wait Until Page Contains Element  display-table
  Element Should Not Contain  display-table  ${GROUP}test  
  Add Group  ${GROUP}test
  Page Should Contain  New Group "${GROUP}test" added
  Go To  ${SERVER}/view_groups
  Wait Until Page Contains Element  display-table
  Element Should Contain  display-table  ${GROUP}test
  
As a Global Manager: I should be able to edit groups
  Go To  ${SERVER}/view_groups
  Wait Until Page Contains Element  display-table
  Click Link  edit-link-${GROUP}test
  Wait Until Page Contains Element  edit-form
  Input Text  name  ${GROUP}edited
  Click Button  submit-button
  Wait Until Page Contains Element  message
  Page Should Contain  Changes to "${GROUP}edited" saved!
  Go To  ${SERVER}/view_groups
  Wait Until Page Contains Element  display-table
  Element Should Contain  display-table  ${GROUP}edited
  Element Should Not Contain  display-table  ${GROUP}test
  
As a Global Manager: I should be able to delete groups
  Go To  ${SERVER}/view_groups
  Wait Until Page Contains Element  display-table
  Click Link  delete-link-${GROUP}edited
  Handle Alert  ACCEPT
  Wait Until Page Contains Element  display-table
  Element Should Not Contain  display-table  ${GROUP}edited

As a Global Manager: I should be able to create a new user
  Add Group  ${GROUP}1
  Add Group  ${GROUP}2
  Go To  ${SERVER}/view_users
  Wait Until Page Contains Element  display-table
  Element Should Not Contain  display-table  ${USERNAME}test  
  Add User  ${USERNAME}test  ${GROUP}1
  Page Should Contain  Registration Successful
  Go To  ${SERVER}/view_users
  Wait Until Page Contains Element  display-table
  Element Should Contain  display-table  ${USERNAME}test
  Element Should Contain  cell-Group(s)-${USERNAME}test  ${GROUP}1
  Element Should Not Contain  cell-Group(s)-${USERNAME}test  ${GROUP}2
  Log Out
  Log In As  ${USERNAME}test  ${PASSWORD}
  Page Should Not Contain  Login Failed
  Page Should Contain  Login Successful
  Log In As User  1

As a Global Manager: I should be able to edit a user
  Go To  ${SERVER}/view_users
  Wait Until Page Contains Element  display-table
  Click Link  edit-link-${USERNAME}test
  Wait Until Page Contains Element  edit-form
  Input Text  first_name  edited first name
  Click Button  submit-button
  Wait Until Page Contains Element  message
  Page Should Contain  Changes to "${USERNAME}test" saved!
  Go To  ${SERVER}/view_users
  Wait Until Page Contains Element  display-table
  Element Should Contain  display-table  edited first name

As a Global Manager: I should be able to assign groups to an existing user
  Add Group to User  ${USERNAME}1  ${GROUP}1
  Page Should Contain  Changes to "${USERNAME}1" saved!
  Add Group to User  ${USERNAME}2  ${GROUP}2
  Add Group to User  ${USERNAME}3  ${GROUP}1
  Go To  ${SERVER}/view_users
  Wait Until Page Contains Element  display-table
  Element Should Contain  cell-Group(s)-${USERNAME}1  ${GROUP}1
  Element Should Contain  cell-Group(s)-${USERNAME}2  ${GROUP}2
  Element Should Contain  cell-Group(s)-${USERNAME}3  ${GROUP}1
  Element Should Not Contain  cell-Group(s)-${USERNAME}1  ${GROUP}2
  Element Should Not Contain  cell-Group(s)-${USERNAME}2  ${GROUP}1
  Element Should Not Contain  cell-Group(s)-${USERNAME}3  ${GROUP}2

As a Global Manager: I should be able to delete a user
  Go To  ${SERVER}/view_users
  Wait Until Page Contains Element  display-table
  Click Link  delete-link-${USERNAME}test
  Handle Alert  ACCEPT
  Wait Until Page Contains Element  display-table
  Element Should Not Contain  display-table  ${USERNAME}test
  
As a Global Manager: I should be able to select any group when uploading data
  Go to  ${SERVER}/workflow
  Element Should Contain  group  ${GROUP}1
  Element Should Contain  group  ${GROUP}2
  
As a Group Manager: I should be able to view other users only in my group(s)
  Log Out
  Log In As User  2
  Go To  ${SERVER}/view_users
  Wait Until Page Contains Element  display-table
  Element Should Not Contain  display-table  ${USERNAME}1
  Element Should Contain  display-table  ${USERNAME}2
  Element Should Not Contain  display-table  ${USERNAME}3
  
As a Group Manager: I should be able to add users to my group(s)
  Go To  ${SERVER}/view_users
  Wait Until Page Contains Element  display-table
  Page Should Contain Element  create-new-button
  Element Should Not Contain  display-table  ${USERNAME}manager_test
  Click Button  create-new-button
  Wait Until Page Contains Element  create-form
  Input Text  username  ${USERNAME}manager_test
  Input Text  password1  ${PASSWORD}
  Input Text  password2  ${PASSWORD}
  Input Text  email  dummy@email.com
  Input Text  first_name  first_name
  Input Text  last_name  last_name
  Element Should Contain  user_groups  ${GROUP}2
  Element Should Not Contain  user_groups  ${GROUP}1
  Select From List By Label  user_groups  ${GROUP}2
  Click Button  submit-button
  Wait Until Page Contains Element  message
  Page Should Contain  Registration Successful
  Go To  ${SERVER}/view_users
  Wait Until Page Contains Element  display-table
  Element Should Contain  display-table  ${USERNAME}manager_test
  
As a Group Manager: I should be able to edit users in my group(s)
  Go To  ${SERVER}/view_users
  Wait Until Page Contains Element  display-table
  Click Link  edit-link-${USERNAME}manager_test
  Wait Until Page Contains Element  edit-form
  Input Text  first_name  edited first name
  Click Button  submit-button
  Wait Until Page Contains Element  message
  Page Should Contain  Changes to "${USERNAME}manager_test" saved!
  Go To  ${SERVER}/view_users
  Wait Until Page Contains Element  display-table
  Element Should Contain  display-table  edited first name

As a Group Manager: I should be able to delete a user in my group(s)
  Go To  ${SERVER}/view_users
  Wait Until Page Contains Element  display-table
  Click Link  delete-link-${USERNAME}manager_test
  Handle Alert  ACCEPT
  Wait Until Page Contains Element  display-table
  Element Should Not Contain  display-table  ${USERNAME}manager_test

As a Group Manager: I should be able to view (but not edit) info on my own group(s) only
  Go To  ${SERVER}/view_groups
  Wait Until Page Contains Element  display-table
  Element Should Not Contain  display-table  ${GROUP}1
  Element Should Contain  display-table  ${GROUP}2
  Page Should Not Contain Element  edit-link-${GROUP}2
  Page Should Not Contain Element  delete-link-${GROUP}2

As a Group Manager: I should be able to select only my own group when uploading data
  Go to  ${SERVER}/workflow
  Element Should Not Contain  group  ${GROUP}1
  Element Should Contain  group  ${GROUP}2
  
As a Basic User: I should be able to view (but not edit) other users only in my group(s)
  Log Out
  Log In As User  3
  Go To  ${SERVER}/view_users
  Wait Until Page Contains Element  display-table
  Element Should Contain  display-table  ${USERNAME}1
  Element Should Not Contain  display-table  ${USERNAME}2
  Element Should Contain  display-table  ${USERNAME}3
  Page Should Not Contain Element  edit-link-${USERNAME}1
  Page Should Not Contain Element  delete-link-${USERNAME}1
  
As a Basic User: I should be able to view (but not edit) info on my own group(s) only
  Go To  ${SERVER}/view_groups
  Wait Until Page Contains Element  display-table
  Element Should Contain  display-table  ${GROUP}1
  Element Should Not Contain  display-table  ${GROUP}2
  Page Should Not Contain Element  edit-link-${GROUP}1
  Page Should Not Contain Element  delete-link-${GROUP}1
  
As a Basic User: I should be able to select only my own group when uploading data
  Go to  ${SERVER}/workflow
  Element Should Contain  group  ${GROUP}1
  Element Should Not Contain  group  ${GROUP}2
  
As Any User: I should be able to upload a .cif file to a group I am a member of
  Log Out
  Log In As User  1
  Go To  ${SERVER}/workflow
  Select From List By Label  group  ${GROUP}1
  Choose File  upload-dataset-file  ${TEST_FILEPATH}
  Click Button  upload-button
  Wait Until Page Contains Element  workflow-display
  Element Should Contain  workflow-display  ${TEST_FILENAME}
  ${workflow url}=  Get Location
  Set suite variable  ${workflow url}
  Upload Copied File  test2.cif  ${GROUP}2
  Upload Copied File  test3.cif  ${GROUP}2
  Upload Copied File  test4.cif  ${GROUP}2
  
As Any User: I should be able to download the current .cif file from the workflow
  Go To  ${workflow url}
  Wait Until Page Contains Element  workflow-display
  Click Link  download-link-current
  Wait Until Created  ${DOWNLOAD_DIR}/${TEST_FILENAME}
  ${original file}=  Get File  ${TEST_FILEPATH}
  ${downloaded file}=  Get File  ${DOWNLOAD_DIR}/${TEST_FILENAME}
  Should Be Equal As Strings  ${original file}  ${downloaded file}
  Remove File  ${DOWNLOAD_DIR}/${TEST_FILENAME}
  
As Any User: I should be able to open the Visualiser for the current .cif from the workflow
  Go To  ${workflow url}
  Wait Until Page Contains Element  workflow-display
  Click Link  visualise-link-current
  Switch Window  NEW
  Wait Until Page Contains  Crystal Structure
  Capture Page Screenshot  visualiser.png
  Close Window
  Switch Window  MAIN

As Any User: I should be able to open the History Panel for the current .cif from the workflow
  Go To  ${workflow url}
  Wait Until Page Contains Element  workflow-display
  Click Link  history-link-current
  Select Frame  plotly_iframe
  Wait Until Page Contains  Dataset Information
  Page Should Contain  ${TEST_FILENAME}
  Sleep  3
  Capture Element Screenshot  plotly_iframe  tree_view_1.png
  Unselect Frame

As Any User: The workflow should auto-populate installed Applications for selection
  Go To  ${workflow url}
  Wait Until Page Contains Element  workflow-display
  Element Should Contain  id_application  Olex2 (Linux)

As a Global Manager: I should be able to select *any* uploaded dataset when starting a new workflow
  Go To  ${SERVER}/workflow
  Element Should Contain  load-dataset-file  ${TEST_FILENAME}
  Element Should Contain  load-dataset-file  test2.cif
  Element Should Contain  load-dataset-file  test3.cif
  Element Should Contain  load-dataset-file  test4.cif
  
As Any User: I should be able to load a dataset and start a new workflow
  Go To  ${SERVER}/workflow
  Select From List By Label  load-dataset-file  ${TEST_FILENAME}
  Click Button  load-button
  Wait Until Page Contains Element  workflow-display
  Element Should Contain  workflow-display  ${TEST_FILENAME}

As a Global Manager: I should be able to view all datasets in the View Datasets table
  Go To  ${SERVER}/view_datasets
  Wait Until Page Contains Element  display-table
  Element Should Contain  display-table  ${TEST_FILENAME}
  Element Should Contain  display-table  test2.cif
  Element Should Contain  display-table  test3.cif
  Element Should Contain  display-table  test4.cif
  
As a Global Manager: I should be able to delete a dataset from any group
  Go To  ${SERVER}/view_datasets
  Element Should Contain  display-table  test4.cif
  Click Link  delete-link-test4.cif
  Handle Alert  ACCEPT
  Wait Until Page Contains Element  display-table
  Element Should Not Contain  display-table  test4.cif
  
As a Group Manager: I should be able to select only datasets from my group(s) when starting a new workflow
  Log Out
  Log In As User  2
  Go To  ${SERVER}/workflow
  Element Should Not Contain  load-dataset-file  ${TEST_FILENAME}
  Element Should Contain  load-dataset-file  test2.cif
  Element Should Contain  load-dataset-file  test3.cif
  
As a Group Manager: I should be able to view only datasets from my group(s) in the View Datasets table
  Go To  ${SERVER}/view_datasets
  Wait Until Page Contains Element  display-table
  Element Should Not Contain  display-table  ${TEST_FILENAME}
  Element Should Contain  display-table  test2.cif
  Element Should Contain  display-table  test3.cif

As a Group Manager: I should be able to delete a dataset from my group(s)
  Go To  ${SERVER}/view_datasets
  Element Should Contain  display-table  test3.cif
  Click Link  delete-link-test3.cif
  Handle Alert  ACCEPT
  Wait Until Page Contains Element  display-table
  Element Should Not Contain  display-table  test3.cif

As a Basic User: I should be able to select only datasets from my group(s) when starting a new workflow
  Log Out
  Log In As User  3
  Go To  ${SERVER}/workflow
  Element Should Contain  load-dataset-file  ${TEST_FILENAME}
  Element Should Not Contain  load-dataset-file  test2.cif
  
As a Basic User: I should be able to view (but not delete) datasets from my group(s) in the View Datasets table
  Go To  ${SERVER}/view_datasets
  Wait Until Page Contains Element  display-table
  Element Should Contain  display-table  ${TEST_FILENAME}
  Element Should Not Contain  display-table  test2.cif
  Page Should Not Contain Link  delete-link-${TEST_FILENAME}
  
As Any User: I should be able to navigate to a dataset's history panel from the View Datasets table
  Go To  ${SERVER}/view_datasets
  Wait Until Page Contains Element  display-table
  Page Should Contain Link  history-link-${TEST_FILENAME}
  Click Link  history-link-${TEST_FILENAME}
  Select Frame  plotly_iframe
  Wait Until Page Contains  Dataset Information
  Page Should Contain  ${TEST_FILENAME}
  Unselect Frame

