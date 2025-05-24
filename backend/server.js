const express = require('express');
const axios = require('axios');
require('dotenv').config();
const cors = require('cors');

const app = express();
app.use(cors());

const client_id = process.env.SPOTIFY_CLIENT_ID;
const client_secret = process.env.SPOTIFY_CLIENT_SECRET;

// Get Spotify Access Token
async function getSpotifyToken() {
  const response = await axios({
    method: 'post',
    url: 'https://accounts.spotify.com/api/token',
    params: { grant_type: 'client_credentials' },
    headers: {
      'Content-Type': 'application/x-www-form-urlencoded',
    },
    auth: {
      username: client_id,
      password: client_secret,
    },
  });
  return response.data.access_token;
}

// Endpoint example to search Spotify
app.get('/search', async (req, res) => {
  const token = await getSpotifyToken();
  const query = req.query.q;
  
  try {
    const response = await axios.get(`https://api.spotify.com/v1/search`, {
      params: {
        q: query,
        type: 'track,playlist',
        limit: 10,
      },
      headers: {
        Authorization: `Bearer ${token}`,
      },
    });
    res.json(response.data);
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

app.get('/audio-features/:id', async (req, res) => {
  const token = await getSpotifyToken();
  const trackId = req.params.id;

  try {
    const response = await axios.get(`https://api.spotify.com/v1/audio-features/${trackId}`, {
      headers: {
        Authorization: `Bearer ${token}`,
      },
    });
    res.json(response.data);
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

const PORT = 3000;
app.listen(PORT, () => {
  console.log(`Server running on http://localhost:${PORT}`);
});
