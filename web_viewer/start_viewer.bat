@echo off
echo Starting Equipment Rental Web Viewer...
echo.
echo The viewer will be accessible at:
echo http://localhost:8585 (on this PC)
echo.
echo To access from other devices, use your PC's IP address:
echo http://YOUR-PC-IP:8585
echo.
echo Press Ctrl+C to stop the viewer
echo.

cd ..
call bnrs\Scripts\activate
python web_viewer/viewer_app.py
pause
