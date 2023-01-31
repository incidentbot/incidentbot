# Troubleshooting

## Errors after enabling the PagerDuty integration

> I've enabled the PagerDuty integration but I'm seeing errors when trying to open a new incident in Slack.
  I'm also seeing errors when viewing the pager section of the UI.

This likely stems from some information missing in the database. To remedy this, open the UI, go to settings, and change the value of `has_run` to `false`.

Restart the application and the issue should be resolved. If not, please file a bug report in the GitHub repo.

> I've made changes in PagerDuty but the bot is out of date. I don't see my teams/schedules/etc.

The bot runs a job every half-hour to update PagerDuty information. If you need it to run sooner, go to the jobs page in the UI and kick off the job manually.
