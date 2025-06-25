# QCrBox Frontend
Django Frontend web app for interacting with QCrBox backend (via API module).

QCrBox Frontend is a user-friendly web application designed to be a graphical user interface for the QCRBox suite of Quantum Crystallography software tools.  The functionality of this web app includes:

- A user login system.
- The ability to create research groups and assign users to them, limiting which datasets they have access to.
- The ability for admins to create and manage users and usergroups.
- The ability for a user to upload `.cif` files from their machine.
- The ability to start interactive sessions using the QCrBox tools, using data which has been uploaded.
- Automatic retrieval of output data products produced in an interactive session, which may then be used as input for additional sessions.
- The ability to download datasets to the user's local computer.
- A 'workflow' view, showing a comprehensive history of the sessions and manipulations which have led to each file in the system.

Please be aware that this web app requires QCRBox to be installed and running in an accessible location.

# Getting Started
Quickstart instructions for getting the QCrBox Frontend running can be found at [here](documentation/deployment_instructions.md).  Other general documentation can be found in the [`documentation/`](documentation/) folder, which is described in detail in the documentation readme at [`documentation/README.md`](documentation/README.md).
