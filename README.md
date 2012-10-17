App Crash Data Collector for GAE (Google App Engine)
=============

This is a backend that works on GAE and lets you easily collect and examine crash logs.

Setup instructions
-------

We assume you have used Google App Engine before and have either appcfg.py, or a nice GUI app - especially for Mac (which you can download from Google) that lets you deploy the app.

So the steps are as follows:
1. Create an app on GAE and get its app_name - you'll need it in step #4.
2. Clone the repo and cd into its dir.
3. Execute in the shell: "cp app.yaml.example app.yaml".
4. Set your app_name in the app.yaml.
5. Execute in the shell: "cp settings.py.example settings.py".
6. Set an email of superadmin for your app in settings.py.
7. Deploy your app to GAE using appcfg.py or a GUI ap