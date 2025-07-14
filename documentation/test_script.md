# Initial conditions

- Purge Frontend Database completely.
- Startup QCrBox Backend on the same machine as this test version of QCrBox Frontend.
- Compose build and run the docker container for QCrBox Frontend.
- Access QCrBox Frontend at `localhost:8888` (by default).


# Group and User Management

- Log in as the automatically created admin user (hereafter referred to as `admin`) by filling out the form on the login page with the username and password you set as environment variables.
- Navigate to `Account > Edit Account`.  Edit one or more user details and click save.  Return to `Account > Edit Account` and verify that the relevant detail has been changed.
- Edit one or more user details and click cancel.  Return to `Account > Edit Account` and verify that the change was not saved.
- Navigate to `Account > Change Password`, fill out matching valid passwords using the form and save.
- Navigate to `Account > Log out`.  Verify that you are returned to the login screen and no options are available on the navbar.
- Log in as `admin` user using the username set as an environment variable and the password entered two steps ago.
- Navigate to `Groups`
- Click `Create New Group`, fill out the form and save the new group as `group1`.
- Repeat this process two more times to create groups `group2` and `group3`.
- Click the `Edit` button in the row for group `group3`.
- Edit one or more details for the group `group3`, save, and verify the changes have been saved.
- Click the `Delete` button in the row for group `group3`, click `ok` on the pop-up dialogue box, and verify that `group3` has been deleted.
- Navigate to `Users`.  Check that there is a single entry in the user list corresponding to `admin`.  The `Group(s)` field should be blank, the `Role` field should list `Admin, Data Manager, Group Manager`.
- Click `Create New User`.  Enter username as `user1`, Select the group `group1` from the groups list.  Click the checkboxes next to `Group Manager`, `Data Manager` and `Global Access`.  Enter valid values for all other fields, making sure you keep a note of the password used.  Save `user1`.
- Click `Create New User`.  Enter username as `user2`, Select the group `group2` from the groups list.  Click the checkboxes next to `Group Manager` and `Data Manager`.  Enter valid values for all other fields, making sure you keep a note of the password used.  Save `user2`.
- Click `Create New User`.  Enter username as `user3`, Select the group `group1` from the groups list.  Enter valid values for all other fields, making sure you keep a note of the password used.  Save `user3`.
- Navigate back to `Users`.  Verify the new users are all present, and all have the correct groups and roles shown:
   - `user1` should have `group1` in the `Group(s)` column and `Admin, Data Manager, Group Manager` in the `Role` column.
   - `user2` should have `group2` in the `Group(s)` column and `Data Manager, Group Manager` in the `Role` column.
   - `user3` should have `group1` in the `Group(s)` column and `User` in the `Role` column.
- Navigate back to `Groups` and check the Groups have been properly updated with the new users.
   - Check that `group1` now has `user1` in the `Ownser(s)` column and `2` in the `# Members` column.
   - Check that `group2` now has `user2` in the `Ownser(s)` column and `1` in the `# Members` column.
- Navigate to `Account > Log out`.
- Log in using the details for `user1`.
- In the `Upload New File` form on the home page, ensure that both `group1` and `group2` are given as options in the drop-down `Group` field.
- Navigate to `Groups`.  Verify that `user1` can see and succesfully edit details for ANY Group.
- Navigate to `Users`.  Verify that `user1` can see and succesfully edit details for ANY User.
- Navigate to `Account > Log out`.
- Log in using the details for `user2`.
- In the `Upload New File` form on the home page, ensure that ONLY `group2` is given as options in the drop-down `Group` field.
- Navigate to `Groups`.  Verify that `user2` can see details ONLY for `group2`, and cannot edit or delete it.
- Navigate to `Users`.  Verify that `user2` can see and succesfully edit details ONLY for themself.
- Navigate to `Account > Log out`.
- Log in using the details for `user2`.
- In the `Upload New File` form on the home page, ensure that ONLY `group1` is given as options in the drop-down `Group` field.
- Navigate to `Groups`.  Verify that `user3` can see details ONLY for `group1`, and cannot edit or delete it.
- Navigate to `Users`.  Verify that `user3` can see details ONLY for `user1` and themself, and cannot edit or delete them.
- Navigate to `Account > Log out`.

# DataSet and Application Management

- Log in as `admin` and navigate to `Home`.
- Upload a valid `.cif` file using the `Upload New File` form, hereafter referred to as `file1`.  Select `group1` for this file, then click upload.
- Verify that you are taken to a workflow for `file1`.
- In the workflow diagram on the left, click the 'download' icon next to `file1`.  Confirm the browser begins a download of `file1`.
- Click the 'eye' icon next to `file1`.  Confirm that a QCrBox_quality visualiser for `file1` is opened in a new browser tab.
- Click the 'clock' icon next to `file1`.  Confirm that you are taken to a Data History panel for `file1`.  The tree view in the left panel should consist of a single red node.
- Click `Start Workflow` on the data history panel, and confirm you return to the workflow for `file1`.
- Click the dropdown for the `Applications` field in the infobox, and ensure all installed QCrBox apps are shown.
- Navigate back to `Home`.
- Upload a valid `.cif` file using the `Upload New File` form, hereafter reffered to as `file2`.  Select `group2` for this file, then click upload.
- Navigate to `Home`.
- Upload a valid `.cif` file using the `Upload New File` form, hereafter reffered to as `file3`.  Select either group for this file, then click upload.
- Log out, then log in as `user1`.
- In the dropdown by 'Load Existing File' on the `Home` page, ensure that both `file1` and `file2` are available as options.
- Navigate to `Data`.  Ensure that `user1` can see information for all three Datasets.
- Ensure the 'delete' option is shown next to each dataset.  Click the delete button beside `file3`, then click `ok` in the popup.  Ensure the dataset is deleted succesfully.
- Log out, then log in as `user3`.
- In the dropdown by 'Load Existing File' on the `Home` page, ensure that ONLY `file1` is available as an option, and there is no delete option.

# Using Applications

- Remain logged in as `user3`.
- Navigate to the `Home` page, and load the existing file `file1`.
- Click the drop-down `Applications` box in the infobox on the right.  For each entry `app i` in the dropdown:
   - Select `app i` from the dropdown.
   - Click `Select Application`
   - Click `Launch Application`
   - Check that a new tab containing the application has opened, and the application has loaded `file1`.
   - Navigate to the new tab, and close the application with the 'x' in the corner of the window.
   - Return to the original tab and click `End Session`.
   - Check that one of the following two options has occurred:
      - If `app1` does not produce an output file, you are returned to the workflow page for `file1` with a banner at the top of the page explaining that no output was produced.
      - If `app1` does produce an output file, you are returned to the workflow page for whatever file was produced in the app.  In this case, check that the 'workflow' panel on the left now shows the new file as a descendant of `file1`.  Click the square next to `file1` to return to the original workflow.
   - Launch another session of `app i`.
   - WITHOUT closing the app in the new tab, click `End Session` in the original tab.  Verify that one of the two 'on ending session' conditions holds true, and verify that the app is no longer open in the second tab.
   - Launch another session of `app i`.  There may be an error message in the new tab due to the previous test force-quitting the session, but check that the new session loads properly regardless.
   - DO NOT click the `End Session` button or close the app window in the new tab!
   - Clear the browser cache, or open the QCrBox Frontend page in a new browser.
   - Log in as `user3` if not already logged in.
   - Navigate to the workflow for `file1`
   - Launch another session of `app i`.
