// API Configuration
const API_BASE_URL = 'http://localhost:8000';
let currentUser = null;
let authToken = null;
let currentSearchType = 'artist';
let currentAlbum = null;

// Initialize app
document.addEventListener('DOMContentLoaded', () => {
    checkAuth();
});

// Authentication Functions
function checkAuth() {
    authToken = localStorage.getItem('authToken');
    if (authToken) {
        loadUserProfile();
    }
}

function toggleAuthForm() {
    const loginForm = document.getElementById('login-form');
    const registerForm = document.getElementById('register-form');

    if (loginForm.style.display === 'none') {
        loginForm.style.display = 'block';
        registerForm.style.display = 'none';
    } else {
        loginForm.style.display = 'none';
        registerForm.style.display = 'block';
    }
}

async function handleRegister(event) {
    event.preventDefault();

    const username = document.getElementById('register-username').value;
    const email = document.getElementById('register-email').value;
    const password = document.getElementById('register-password').value;

    try {
        const response = await fetch(`${API_BASE_URL}/register`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ username, email, password })
        });

        const data = await response.json();

        if (response.ok) {
            showToast('Registration successful! Please login.', 'success');
            toggleAuthForm();
        } else {
            showToast(data.detail || 'Registration failed', 'error');
        }
    } catch (error) {
        showToast('Network error. Please try again.', 'error');
    }
}

async function handleLogin(event) {
    event.preventDefault();

    const username = document.getElementById('login-username').value;
    const password = document.getElementById('login-password').value;

    try {
        const formData = new URLSearchParams();
        formData.append('username', username);
        formData.append('password', password);

        const response = await fetch(`${API_BASE_URL}/login`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
            body: formData
        });

        const data = await response.json();

        if (response.ok) {
            authToken = data.access_token;
            localStorage.setItem('authToken', authToken);
            showToast('Login successful!', 'success');
            await loadUserProfile();
            showSection('search');
        } else {
            showToast(data.detail || 'Login failed', 'error');
        }
    } catch (error) {
        showToast('Network error. Please try again.', 'error');
    }
}

function logout() {
    authToken = null;
    currentUser = null;
    localStorage.removeItem('authToken');
    document.getElementById('nav-links').style.display = 'none';
    showSection('auth');
    showToast('Logged out successfully', 'success');
}

async function loadUserProfile() {
    try {
        const response = await fetch(`${API_BASE_URL}/user/profile`, {
            headers: { 'Authorization': `Bearer ${authToken}` }
        });

        if (response.ok) {
            currentUser = await response.json();
            document.getElementById('nav-links').style.display = 'flex';
            document.getElementById('auth-section').classList.remove('active');
        } else {
            logout();
        }
    } catch (error) {
        showToast('Failed to load profile', 'error');
        logout();
    }
}

// Navigation
function showSection(sectionName) {
    const sections = document.querySelectorAll('.section');
    sections.forEach(section => section.classList.remove('active'));

    const targetSection = document.getElementById(`${sectionName}-section`);
    if (targetSection) {
        targetSection.classList.add('active');

        // Load data for specific sections
        if (sectionName === 'profile') {
            loadProfile();
        } else if (sectionName === 'activity') {
            loadActivity();
        } else if (sectionName === 'recommendations') {
            loadRecommendations();
        }
    }
}

// Search Functions
function setSearchType(type) {
    currentSearchType = type;
    document.getElementById('search-artist-btn').classList.toggle('active', type === 'artist');
    document.getElementById('search-album-btn').classList.toggle('active', type === 'album');
}

async function handleSearch(event) {
    event.preventDefault();

    const searchInput = document.getElementById('search-input').value;
    const resultsContainer = document.getElementById('search-results');
    resultsContainer.innerHTML = '<div class="loading"></div>';

    try {
        let endpoint;
        if (currentSearchType === 'artist') {
            endpoint = `/search/artist/${encodeURIComponent(searchInput)}`;
        } else {
            endpoint = `/search/album/${encodeURIComponent(searchInput)}`;
        }

        const response = await fetch(`${API_BASE_URL}${endpoint}`, {
            headers: { 'Authorization': `Bearer ${authToken}` }
        });

        if (response.ok) {
            const albums = await response.json();
            displayAlbums(albums, resultsContainer);
        } else {
            resultsContainer.innerHTML = '<div class="empty-state"><h3>No results found</h3></div>';
        }
    } catch (error) {
        resultsContainer.innerHTML = '<div class="empty-state"><h3>Search failed</h3></div>';
        showToast('Search failed. Please try again.', 'error');
    }
}

function displayAlbums(albums, container) {
    if (albums.length === 0) {
        container.innerHTML = '<div class="empty-state"><h3>No albums found</h3></div>';
        return;
    }

    container.innerHTML = albums.map(album => `
        <div class="album-card" onclick="openAlbumModal('${album.album_id}', ${JSON.stringify(album).replace(/"/g, '&quot;')})">
            <img src="${album.cover}" alt="${album.album_name}" class="album-cover">
            <div class="album-info">
                <h3>${album.album_name}</h3>
                <p>${album.artist_name}</p>
                <p style="font-size: 0.75rem;">${album.release_date}</p>
            </div>
        </div>
    `).join('');
}

// Album Modal
function openAlbumModal(albumId, albumData) {
    currentAlbum = albumData;
    const modal = document.getElementById('album-modal');
    const detailsContainer = document.getElementById('album-details');

    detailsContainer.innerHTML = `
        <div class="album-detail">
            <img src="${albumData.cover}" alt="${albumData.album_name}" class="album-detail-cover">
            <div class="album-detail-info">
                <h2>${albumData.album_name}</h2>
                <p><strong>Artist:</strong> ${albumData.artist_name}</p>
                <p><strong>Release Date:</strong> ${albumData.release_date}</p>
                <div style="margin-top: 1rem;">
                    <button class="btn-secondary" onclick="addToFavorites('${albumData.album_id}')">Add to Favorites</button>
                </div>
            </div>
        </div>
        
        <div class="review-form">
            <h3>Rate & Review</h3>
            <div class="rating-input" id="rating-stars">
                ${[1, 2, 3, 4, 5].map(i => `
                    <button onclick="selectRating(${i})">★</button>
                `).join('')}
            </div>
            <textarea id="review-text" placeholder="Write your review (optional)..."></textarea>
            <button class="btn-primary" onclick="submitReview('${albumData.album_id}')">Submit Review</button>
            <button class="btn-danger" onclick="deleteReview('${albumData.album_id}')" style="margin-top: 0.5rem;">Delete Review</button>
        </div>
    `;

    modal.style.display = 'flex';
}

function closeAlbumModal() {
    document.getElementById('album-modal').style.display = 'none';
    currentAlbum = null;
}

let selectedRating = 0;

function selectRating(rating) {
    selectedRating = rating;
    const stars = document.querySelectorAll('#rating-stars button');
    stars.forEach((star, index) => {
        star.classList.toggle('selected', index < rating);
    });
}

async function submitReview(albumId) {
    if (selectedRating === 0) {
        showToast('Please select a rating', 'error');
        return;
    }

    const reviewText = document.getElementById('review-text').value;

    try {
        const response = await fetch(`${API_BASE_URL}/album/${albumId}/rating`, {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${authToken}`,
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                rating: selectedRating,
                review: reviewText || ""
            })
        });

        const data = await response.json();

        if (response.ok) {
            showToast('Review submitted successfully!', 'success');
            closeAlbumModal();
            selectedRating = 0;
        } else {
            showToast(data.detail || 'Failed to submit review', 'error');
        }
    } catch (error) {
        showToast('Network error. Please try again.', 'error');
    }
}

async function deleteReview(albumId) {
    try {
        const response = await fetch(`${API_BASE_URL}/album/${albumId}/delete_rating`, {
            method: 'DELETE',
            headers: { 'Authorization': `Bearer ${authToken}` }
        });

        const data = await response.json();

        if (response.ok) {
            showToast('Review deleted successfully!', 'success');
            closeAlbumModal();
        } else {
            showToast(data.detail || 'Failed to delete review', 'error');
        }
    } catch (error) {
        showToast('Network error. Please try again.', 'error');
    }
}

async function addToFavorites(albumId) {
    try {
        const response = await fetch(`${API_BASE_URL}/album/${albumId}/add_favorite`, {
            method: 'POST',
            headers: { 'Authorization': `Bearer ${authToken}` }
        });

        const data = await response.json();

        if (response.ok) {
            showToast('Added to favorites!', 'success');
        } else {
            showToast(data.detail || 'Failed to add to favorites', 'error');
        }
    } catch (error) {
        showToast('Network error. Please try again.', 'error');
    }
}

// Profile Functions
async function loadProfile() {
    const container = document.getElementById('profile-content');
    container.innerHTML = '<div class="loading"></div>';

    try {
        const response = await fetch(`${API_BASE_URL}/user/profile`, {
            headers: { 'Authorization': `Bearer ${authToken}` }
        });

        if (response.ok) {
            const profile = await response.json();
            displayProfile(profile, container);
        } else {
            container.innerHTML = '<div class="empty-state"><h3>Failed to load profile</h3></div>';
        }
    } catch (error) {
        container.innerHTML = '<div class="empty-state"><h3>Failed to load profile</h3></div>';
        showToast('Failed to load profile', 'error');
    }
}

function displayProfile(profile, container) {
    container.innerHTML = `
        <div class="profile-header">
            <img src="${profile.picture || 'https://via.placeholder.com/150'}" alt="${profile.username}" class="profile-picture">
            <div class="profile-info">
                <h2>${profile.username}</h2>
                <div class="profile-stats">
                    <div class="stat">
                        <div class="stat-number">${profile.followers_count}</div>
                        <div class="stat-label">Followers</div>
                    </div>
                    <div class="stat">
                        <div class="stat-number">${profile.following_count}</div>
                        <div class="stat-label">Following</div>
                    </div>
                    <div class="stat">
                        <div class="stat-number">${profile.reviews.length}</div>
                        <div class="stat-label">Reviews</div>
                    </div>
                    <div class="stat">
                        <div class="stat-number">${profile.favorites.length}</div>
                        <div class="stat-label">Favorites</div>
                    </div>
                </div>
                <p class="profile-bio">${profile.bio || 'No bio yet.'}</p>
                <div class="profile-actions">
                    <button class="btn-secondary" onclick="openEditModal()">Edit Profile</button>
                    <button class="btn-secondary" onclick="showFollowers()">View Followers</button>
                    <button class="btn-secondary" onclick="showFollowing()">View Following</button>
                </div>
            </div>
        </div>
        
        <div class="profile-tabs">
            <button class="active" onclick="showProfileTab('favorites')">Favorites</button>
            <button onclick="showProfileTab('reviews')">Reviews</button>
        </div>
        
        <div id="profile-tab-content">
            ${displayFavorites(profile.favorites)}
        </div>
    `;
}

function showProfileTab(tab) {
    const buttons = document.querySelectorAll('.profile-tabs button');
    buttons.forEach(btn => btn.classList.remove('active'));
    event.target.classList.add('active');

    const content = document.getElementById('profile-tab-content');

    if (tab === 'favorites') {
        loadProfile(); // Reload to get fresh data
    } else if (tab === 'reviews') {
        loadUserReviews();
    }
}

function displayFavorites(favorites) {
    if (favorites.length === 0) {
        return '<div class="empty-state"><h3>No favorites yet</h3><p>Start adding albums to your favorites!</p></div>';
    }

    return `<div class="album-grid">${favorites.map(album => `
        <div class="album-card" onclick="openAlbumModal('${album.album_id}', ${JSON.stringify(album).replace(/"/g, '&quot;')})">
            <img src="${album.cover}" alt="${album.album_name}" class="album-cover">
            <div class="album-info">
                <h3>${album.album_name}</h3>
                <p>${album.artist_name}</p>
            </div>
        </div>
    `).join('')}</div>`;
}

async function loadUserReviews() {
    const content = document.getElementById('profile-tab-content');
    content.innerHTML = '<div class="loading"></div>';

    try {
        const response = await fetch(`${API_BASE_URL}/user/profile`, {
            headers: { 'Authorization': `Bearer ${authToken}` }
        });

        if (response.ok) {
            const profile = await response.json();
            displayReviews(profile.reviews, content);
        }
    } catch (error) {
        content.innerHTML = '<div class="empty-state"><h3>Failed to load reviews</h3></div>';
    }
}

function displayReviews(reviews, container) {
    if (reviews.length === 0) {
        container.innerHTML = '<div class="empty-state"><h3>No reviews yet</h3><p>Start reviewing albums!</p></div>';
        return;
    }

    container.innerHTML = reviews.map(review => `
        <div class="review-card">
            <div class="review-header">
                <img src="${review.cover}" alt="${review.album_name}" class="review-cover">
                <div class="review-info">
                    <h4>${review.album_name}</h4>
                    <p>${review.artist_name}</p>
                    <div class="rating">
                        ${[1, 2, 3, 4, 5].map(i => `
                            <span class="star ${i <= review.rating ? 'filled' : 'empty'}">★</span>
                        `).join('')}
                    </div>
                </div>
            </div>
            ${review.review ? `<p class="review-text">${review.review}</p>` : ''}
        </div>
    `).join('');
}

// Edit Profile
function openEditModal() {
    const modal = document.getElementById('edit-profile-modal');
    document.getElementById('edit-bio').value = currentUser.bio || '';
    document.getElementById('edit-picture').value = currentUser.picture || '';
    modal.style.display = 'flex';
}

function closeEditModal() {
    document.getElementById('edit-profile-modal').style.display = 'none';
}

async function handleUpdateProfile(event) {
    event.preventDefault();

    const bio = document.getElementById('edit-bio').value;
    const picture = document.getElementById('edit-picture').value;

    try {
        // Update bio
        const bioResponse = await fetch(`${API_BASE_URL}/user/update_bio`, {
            method: 'PUT',
            headers: {
                'Authorization': `Bearer ${authToken}`,
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ bio })
        });

        // Update picture if provided
        if (picture) {
            await fetch(`${API_BASE_URL}/user/update_picture`, {
                method: 'PUT',
                headers: {
                    'Authorization': `Bearer ${authToken}`,
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ picture })
            });
        }

        if (bioResponse.ok) {
            showToast('Profile updated successfully!', 'success');
            closeEditModal();
            loadProfile();
        } else {
            showToast('Failed to update profile', 'error');
        }
    } catch (error) {
        showToast('Network error. Please try again.', 'error');
    }
}

// Followers/Following
async function showFollowers() {
    try {
        const response = await fetch(`${API_BASE_URL}/user/get_followers`, {
            headers: { 'Authorization': `Bearer ${authToken}` }
        });

        if (response.ok) {
            const followers = await response.json();
            displayUserList(followers, 'Followers');
        }
    } catch (error) {
        showToast('Failed to load followers', 'error');
    }
}

async function showFollowing() {
    try {
        const response = await fetch(`${API_BASE_URL}/user/get_following`, {
            headers: { 'Authorization': `Bearer ${authToken}` }
        });

        if (response.ok) {
            const following = await response.json();
            displayUserList(following, 'Following');
        }
    } catch (error) {
        showToast('Failed to load following', 'error');
    }
}

function displayUserList(users, title) {
    if (users.length === 0) {
        showToast(`No ${title.toLowerCase()} yet`, 'error');
        return;
    }

    const content = users.map(user => `
        <div class="user-card">
            <div>
                <h4>${user.username}</h4>
            </div>
            <button class="btn-secondary" onclick="viewUserProfile('${user.username}')">View Profile</button>
        </div>
    `).join('');

    document.getElementById('profile-tab-content').innerHTML = `
        <h3>${title}</h3>
        ${content}
    `;
}

async function viewUserProfile(username) {
    try {
        const response = await fetch(`${API_BASE_URL}/user/${username}/profile`, {
            headers: { 'Authorization': `Bearer ${authToken}` }
        });

        if (response.ok) {
            const profile = await response.json();
            displayOtherUserProfile(profile);
        }
    } catch (error) {
        showToast('Failed to load user profile', 'error');
    }
}

function displayOtherUserProfile(profile) {
    const container = document.getElementById('profile-content');

    container.innerHTML = `
        <div class="profile-header">
            <img src="${profile.picture || 'https://via.placeholder.com/150'}" alt="${profile.username}" class="profile-picture">
            <div class="profile-info">
                <h2>${profile.username}</h2>
                <div class="profile-stats">
                    <div class="stat">
                        <div class="stat-number">${profile.followers_count}</div>
                        <div class="stat-label">Followers</div>
                    </div>
                    <div class="stat">
                        <div class="stat-number">${profile.following_count}</div>
                        <div class="stat-label">Following</div>
                    </div>
                    <div class="stat">
                        <div class="stat-number">${profile.reviews.length}</div>
                        <div class="stat-label">Reviews</div>
                    </div>
                </div>
                <p class="profile-bio">${profile.bio || 'No bio yet.'}</p>
                <div class="profile-actions">
                    <button class="btn-secondary" onclick="followUser(${profile.id})">Follow</button>
                    <button class="btn-danger" onclick="unfollowUser(${profile.id})">Unfollow</button>
                </div>
            </div>
        </div>
        
        <h3>Reviews</h3>
        <div id="other-user-reviews">
            ${profile.reviews.map(review => `
                <div class="review-card">
                    <div class="review-header">
                        <img src="${review.cover}" alt="${review.album_name}" class="review-cover">
                        <div class="review-info">
                            <h4>${review.album_name}</h4>
                            <p>${review.artist_name}</p>
                            <div class="rating">
                                ${[1, 2, 3, 4, 5].map(i => `
                                    <span class="star ${i <= review.rating ? 'filled' : 'empty'}">★</span>
                                `).join('')}
                            </div>
                        </div>
                    </div>
                    ${review.review ? `<p class="review-text">${review.review}</p>` : ''}
                </div>
            `).join('')}
        </div>
    `;

    showSection('profile');
}

async function followUser(userId) {
    try {
        const response = await fetch(`${API_BASE_URL}/user/${userId}/follow`, {
            method: 'POST',
            headers: { 'Authorization': `Bearer ${authToken}` }
        });

        const data = await response.json();

        if (response.ok) {
            showToast('User followed!', 'success');
        } else {
            showToast(data.detail || 'Failed to follow user', 'error');
        }
    } catch (error) {
        showToast('Network error. Please try again.', 'error');
    }
}

async function unfollowUser(userId) {
    try {
        const response = await fetch(`${API_BASE_URL}/user/${userId}/unfollow`, {
            method: 'DELETE',
            headers: { 'Authorization': `Bearer ${authToken}` }
        });

        const data = await response.json();

        if (response.ok) {
            showToast('User unfollowed!', 'success');
        } else {
            showToast(data.detail || 'Failed to unfollow user', 'error');
        }
    } catch (error) {
        showToast('Network error. Please try again.', 'error');
    }
}

// Activity Feed
async function loadActivity() {
    const container = document.getElementById('activity-feed');
    container.innerHTML = '<div class="loading"></div>';

    try {
        const response = await fetch(`${API_BASE_URL}/user/friends_activity`, {
            headers: { 'Authorization': `Bearer ${authToken}` }
        });

        if (response.ok) {
            const activities = await response.json();
            displayActivities(activities, container);
        } else {
            container.innerHTML = '<div class="empty-state"><h3>No activity yet</h3></div>';
        }
    } catch (error) {
        container.innerHTML = '<div class="empty-state"><h3>Failed to load activity</h3></div>';
        showToast('Failed to load activity', 'error');
    }
}

function displayActivities(activities, container) {
    if (activities.length === 0) {
        container.innerHTML = '<div class="empty-state"><h3>No activity yet</h3><p>Follow users to see their reviews!</p></div>';
        return;
    }

    container.innerHTML = activities.map(activity => `
        <div class="activity-card">
            <img src="${activity.cover}" alt="${activity.album_name}" class="activity-cover">
            <div class="activity-info">
                <h4>${activity.album_name}</h4>
                <p>${activity.artist_name}</p>
                <div class="rating">
                    ${[1, 2, 3, 4, 5].map(i => `
                        <span class="star ${i <= activity.rating ? 'filled' : 'empty'}">★</span>
                    `).join('')}
                </div>
                ${activity.review ? `<p class="review-text">${activity.review}</p>` : ''}
            </div>
        </div>
    `).join('');
}

// Recommendations
async function loadRecommendations() {
    const container = document.getElementById('recommendations-grid');
    container.innerHTML = '<div class="loading"></div>';

    try {
        const response = await fetch(`${API_BASE_URL}/user/get_recommendations`, {
            headers: { 'Authorization': `Bearer ${authToken}` }
        });

        if (response.ok) {
            const albums = await response.json();
            displayAlbums(albums, container);
        } else {
            container.innerHTML = '<div class="empty-state"><h3>No recommendations yet</h3></div>';
        }
    } catch (error) {
        container.innerHTML = '<div class="empty-state"><h3>Failed to load recommendations</h3></div>';
        showToast('Failed to load recommendations', 'error');
    }
}

// User Search
async function handleUserSearch(event) {
    event.preventDefault();

    const username = document.getElementById('user-search-input').value;

    try {
        const response = await fetch(`${API_BASE_URL}/user/${username}/search`, {
            headers: { 'Authorization': `Bearer ${authToken}` }
        });

        if (response.ok) {
            const user = await response.json();
            viewUserProfile(username);
        } else {
            showToast('User not found', 'error');
        }
    } catch (error) {
        showToast('Search failed. Please try again.', 'error');
    }
}

// Toast Notification
function showToast(message, type = 'info') {
    const toast = document.getElementById('toast');
    toast.textContent = message;
    toast.className = `toast ${type} show`;

    setTimeout(() => {
        toast.classList.remove('show');
    }, 3000);
}

// Close modals when clicking outside
window.onclick = function (event) {
    const albumModal = document.getElementById('album-modal');
    const editModal = document.getElementById('edit-profile-modal');

    if (event.target === albumModal) {
        closeAlbumModal();
    }
    if (event.target === editModal) {
        closeEditModal();
    }
}
