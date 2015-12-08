@echo !!Output Starting Import

@set this_path=%~dp0
@echo %this_path%

CALL python "%this_path%hobbes_input.py" %*
@echo !!Output complete
