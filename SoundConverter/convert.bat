for %%f in (*.bnk) do %~dp0bnkextr.exe %%f
ping localhost /n 1 >NUL
for %%f in (*.wem) do %~dp0ww2ogg.exe %%f --pcb %~dp0packed_codebooks_aoTuV_603.bin
ping localhost /n 1 >NUL
for %%f in (*.ogg) do %~dp0revorb.exe %%f
ping localhost /n 1 >NUL
del *.wem
del *.bnk
del *.exe
del *.h