@echo off
echo ===================================================
echo        UPDATING CEM COPOK BOT ON GITHUB
echo ===================================================
git add .
git commit -m "Automated update"
git push origin main
echo ===================================================
echo ✅ Done! Your bot will now redeploy on Railway!
echo ===================================================
pause
