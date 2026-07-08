# Equipment Rental System - Read-Only Web Viewer

This is a separate, read-only web interface for viewing equipment rental status across your local network.

## Features

- View available equipment in real-time
- See currently rented equipment with user details (including rental date and comments)
- Filter by equipment type
- Search by equipment name
- View complete rental history with search and sorting
- Auto-refresh every 30 seconds
- 100% read-only - no modifications possible
- Accessible from any device on your local network
- **Independent user sessions** - each user has their own filters (filters don't affect other users)

## How to Use

### Starting the Viewer

1. Open a terminal/command prompt
2. Navigate to the project root directory
3. Activate your virtual environment (if using one):
   ```bash
   bnrs\Scripts\activate
   ```
4. Run the viewer:
   ```bash
   python web_viewer/viewer_app.py
   ```

### Accessing from Other Devices

1. Find your PC's local IP address:
   - Windows: Open Command Prompt and type `ipconfig`
   - Look for "IPv4 Address" (usually something like 192.168.1.XXX)

2. On any other device on the same network:
   - Open a web browser
   - Type: `http://YOUR-PC-IP:8081`
   - Example: `http://192.168.1.100:8081`

### Stopping the Viewer

- Press `Ctrl+C` in the terminal where the viewer is running

## Technical Details

- **Port:** 8081 (different from main app to avoid conflicts)
- **Host:** 0.0.0.0 (accessible from network)
- **Auto-refresh:** Every 30 seconds
- **Database:** Reads from same `rental.db` as main application
- **Dependencies:** Uses same requirements as main app

## Security Notes

- This viewer is READ-ONLY - no data can be modified
- Only accessible within your local network (not from internet)
- No authentication required (suitable for trusted local networks)
- If you need authentication, it can be added

## Troubleshooting

### Can't access from other devices?
- Check Windows Firewall settings
- Make sure port 8081 is allowed
- Verify both devices are on the same network

### Data not updating?
- Click the "Refresh" button manually
- Check that main database file is accessible
- Ensure main app isn't blocking database access

### Port already in use?
- Change port in `viewer_app.py` (line with `port=8081`)
- Use any port number above 1024 (e.g., 8082, 8090, etc.)

## Running Both Apps Simultaneously

You can run both the main app and the viewer at the same time:
1. Start your main app (`main.py`) in one terminal
2. Start the viewer (`web_viewer/viewer_app.py`) in another terminal
3. Both will access the same database without conflicts
