# Project instructions

## Temporary files

- Never use `/tmp` or any other system temp directory for temporary files in this project.
  Write temp/intermediate files to the current working directory with the `_cctmp.` prefix
  (e.g. `_cctmp.gh.json`, `_cctmp.days.json`) and delete them once the task is done.
