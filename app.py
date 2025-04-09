import streamlit as st
import pandas as pd
import plotly.express as px
import json
import os
from datetime import datetime
import requests
from PIL import Image
import io
import base64
import hashlib
import secrets
import time

# Function to convert image to base64
def get_image_base64(image):
    buffered = io.BytesIO()
    image.save(buffered, format="PNG")
    return base64.b64encode(buffered.getvalue()).decode()

# Function to save uploaded image
def save_uploaded_image(uploaded_file):
    if uploaded_file is not None:
        image = Image.open(uploaded_file)
        # Resize image to maintain consistency
        image = image.resize((200, 300))
        # Convert to base64
        return get_image_base64(image)
    return None

# Function to get book details from ISBN
def get_book_details(isbn):
    try:
        response = requests.get(f'https://openlibrary.org/api/books?bibkeys=ISBN:{isbn}&format=json&jscmd=data')
        data = response.json()
        if f'ISBN:{isbn}' in data:
            book_data = data[f'ISBN:{isbn}']
            return {
                'title': book_data.get('title', ''),
                'author': ', '.join([author.get('name', '') for author in book_data.get('authors', [])]),
                'cover_url': book_data.get('cover', {}).get('medium', ''),
                'publish_date': book_data.get('publish_date', ''),
                'publisher': book_data.get('publishers', [{}])[0].get('name', '')
            }
    except:
        return None

# Page configuration
st.set_page_config(
    page_title="Personal Library Manager",
    page_icon="📚",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize session state for authentication
if 'authenticated' not in st.session_state:
    st.session_state.authenticated = False
if 'current_user' not in st.session_state:
    st.session_state.current_user = None
if 'users' not in st.session_state:
    st.session_state.users = {}
if 'session_id' not in st.session_state:
    st.session_state.session_id = secrets.token_hex(16)

# Function to load users from file
def load_users():
    if os.path.exists('users.json'):
        with open('users.json', 'r') as f:
            st.session_state.users = json.load(f)

# Function to save users to file
def save_users():
    with open('users.json', 'w') as f:
        json.dump(st.session_state.users, f)

# Function to hash password
def hash_password(password):
    salt = secrets.token_hex(16)
    return hashlib.sha256((password + salt).encode()).hexdigest(), salt

# Function to verify password
def verify_password(password, hashed_password, salt):
    return hashlib.sha256((password + salt).encode()).hexdigest() == hashed_password

# Function to check authentication
def check_auth():
    if not st.session_state.authenticated:
        st.warning("Please login to access the library manager.")
        return False
    return True

# Function to save session data
def save_session_data():
    if st.session_state.authenticated and st.session_state.current_user:
        session_data = {
            'session_id': st.session_state.session_id,
            'username': st.session_state.current_user,
            'timestamp': datetime.now().isoformat()
        }
        with open(f'session_{st.session_state.session_id}.json', 'w') as f:
            json.dump(session_data, f)

# Function to load session data
def load_session_data():
    try:
        session_files = [f for f in os.listdir() if f.startswith('session_') and f.endswith('.json')]
        if session_files:
            latest_session = max(session_files, key=lambda x: os.path.getmtime(x))
            with open(latest_session, 'r') as f:
                session_data = json.load(f)
                # Check if session is less than 24 hours old
                session_time = datetime.fromisoformat(session_data['timestamp'])
                if (datetime.now() - session_time).total_seconds() < 86400:  # 24 hours in seconds
                    st.session_state.session_id = session_data['session_id']
                    st.session_state.current_user = session_data['username']
                    st.session_state.authenticated = True
    except:
        pass

# Load session data on startup
load_session_data()

# Load users on startup
load_users()

# Login/Signup Page
def auth_page():
    st.title("🔐 Library Manager Authentication")
    
    tab1, tab2 = st.tabs(["Login", "Sign Up"])
    
    with tab1:
        with st.form("login_form"):
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")
            remember_me = st.checkbox("Remember me")
            submit = st.form_submit_button("Login")
            
            if submit:
                if username in st.session_state.users:
                    stored_hash, salt = st.session_state.users[username]['password']
                    if verify_password(password, stored_hash, salt):
                        st.session_state.authenticated = True
                        st.session_state.current_user = username
                        if remember_me:
                            save_session_data()
                        st.success("Login successful!")
                        st.rerun()
                    else:
                        st.error("Invalid password")
                else:
                    st.error("Username not found")
    
    with tab2:
        with st.form("signup_form"):
            new_username = st.text_input("Choose Username")
            new_password = st.text_input("Choose Password", type="password")
            confirm_password = st.text_input("Confirm Password", type="password")
            submit = st.form_submit_button("Sign Up")
            
            if submit:
                if new_username in st.session_state.users:
                    st.error("Username already exists")
                elif new_password != confirm_password:
                    st.error("Passwords do not match")
                else:
                    hashed_password, salt = hash_password(new_password)
                    st.session_state.users[new_username] = {
                        'password': (hashed_password, salt),
                        'books': [],
                        'collections': {}
                    }
                    save_users()
                    st.success("Account created successfully! Please login.")

# Main application
def main_app():
    # Sidebar navigation with enhanced styling
    st.sidebar.title("📚 Library Manager")
    st.sidebar.markdown("---")
    
    # Add logout button
    if st.sidebar.button("Logout"):
        st.session_state.authenticated = False
        st.session_state.current_user = None
        # Remove session file
        session_file = f'session_{st.session_state.session_id}.json'
        if os.path.exists(session_file):
            os.remove(session_file)
        st.rerun()
    
    page = st.sidebar.radio(
        "Navigation",
        ["Dashboard", "Add Book", "View Library", "Collections", "Statistics"],
        label_visibility="collapsed"
    )

    # Dashboard Page
    if page == "Dashboard":
        st.title("📚 Personal Library Dashboard")
        
        # Animated metrics
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric(
                "Total Books",
                len(st.session_state.users[st.session_state.current_user]['books']),
                delta=None,
                delta_color="normal"
            )
        
        with col2:
            read_books = sum(1 for book in st.session_state.users[st.session_state.current_user]['books'] if book.get('status') == 'Read')
            st.metric(
                "Books Read",
                read_books,
                delta=None,
                delta_color="normal"
            )
        
        with col3:
            collections_count = len(st.session_state.users[st.session_state.current_user]['collections'])
            st.metric(
                "Collections",
                collections_count,
                delta=None,
                delta_color="normal"
            )
        
        # Recent additions with enhanced styling
        st.subheader("Recent Additions")
        recent_books = sorted(st.session_state.users[st.session_state.current_user]['books'], key=lambda x: x.get('date_added', ''), reverse=True)[:5]
        for book in recent_books:
            with st.container():
                st.markdown('<div class="book-card">', unsafe_allow_html=True)
                col1, col2 = st.columns([1, 3])
                with col1:
                    if book.get('cover_image'):
                        st.image(f"data:image/png;base64,{book['cover_image']}", width=150)
                    elif book.get('cover_url'):
                        st.image(book['cover_url'], width=150)
                    else:
                        st.image("https://via.placeholder.com/150x200?text=No+Cover", width=150)
                with col2:
                    st.write(f"**{book['title']}**")
                    st.write(f"by {book['author']}")
                    st.write(f"Status: {book['status']}")
                    st.write(f"Rating: {'⭐' * book['rating']}")
                    if book.get('collections'):
                        st.write(f"Collections: {', '.join(book['collections'])}")
                st.markdown('</div>', unsafe_allow_html=True)

    # Add Book Page
    elif page == "Add Book":
        st.title("📖 Add New Book")
        
        # Initialize form state
        if 'form_submitted' not in st.session_state:
            st.session_state.form_submitted = False
        if 'form_clear' not in st.session_state:
            st.session_state.form_clear = False
        
        with st.form("add_book_form"):
            # Single column layout
            isbn = st.text_input("ISBN", placeholder="Enter ISBN to auto-fill details", value="" if st.session_state.form_clear else None)
            if isbn:
                book_details = get_book_details(isbn)
                if book_details:
                    title = st.text_input("Title", value=book_details['title'] if not st.session_state.form_clear else "")
                    author = st.text_input("Author", value=book_details['author'] if not st.session_state.form_clear else "")
                    if book_details['cover_url']:
                        st.image(book_details['cover_url'], width=150)
                else:
                    title = st.text_input("Title", value="" if st.session_state.form_clear else None)
                    author = st.text_input("Author", value="" if st.session_state.form_clear else None)
            else:
                title = st.text_input("Title", value="" if st.session_state.form_clear else None)
                author = st.text_input("Author", value="" if st.session_state.form_clear else None)
            
            # Add image upload section
            st.markdown("### 📸 Book Cover")
            uploaded_image = st.file_uploader("Upload book cover image", type=["jpg", "jpeg", "png"])
            if uploaded_image:
                st.image(uploaded_image, width=150)
            
            # Book details in single column
            rating = st.slider("Rating", 1, 5, 3)
            status = st.selectbox("Status", ["Read", "Unread", "Reading"])
            date_added = st.date_input("Date Added", datetime.now())
            collections = st.multiselect(
                "Collections",
                list(st.session_state.users[st.session_state.current_user]['collections'].keys()),
                help="Select collections for this book"
            )
            
            submit_button = st.form_submit_button("Add Book")
            
            if submit_button:
                if not title or not author:
                    st.error("Please fill in all required fields (Title and Author)")
                else:
                    new_book = {
                        "title": title,
                        "author": author,
                        "isbn": isbn,
                        "rating": rating,
                        "status": status,
                        "date_added": date_added.strftime("%Y-%m-%d"),
                        "collections": collections
                    }
                    
                    # Save uploaded image if exists
                    if uploaded_image:
                        new_book["cover_image"] = save_uploaded_image(uploaded_image)
                    elif book_details and book_details.get('cover_url'):
                        new_book["cover_url"] = book_details['cover_url']
                    
                    st.session_state.users[st.session_state.current_user]['books'].append(new_book)
                    save_users()
                    st.success("Book added successfully!")
                    
                    # Set form clear flag and trigger refresh
                    st.session_state.form_clear = True
                    st.session_state.form_submitted = True
                    
                    # Add a small delay before refresh to show success message
                    time.sleep(1.5)
                    st.rerun()
        
        # Reset form state after refresh
        if st.session_state.form_submitted:
            st.session_state.form_submitted = False
            st.session_state.form_clear = False

    # Collections Page
    elif page == "Collections":
        st.title("📚 Collections")
        
        # Create new collection
        with st.form("new_collection"):
            collection_name = st.text_input("Collection Name")
            collection_description = st.text_area("Description")
            if st.form_submit_button("Create Collection"):
                if collection_name:
                    st.session_state.users[st.session_state.current_user]['collections'][collection_name] = {
                        "description": collection_description,
                        "books": []
                    }
                    save_users()
                    st.success(f"Collection '{collection_name}' created!")
        
        # Display collections
        for collection_name, collection_data in st.session_state.users[st.session_state.current_user]['collections'].items():
            with st.expander(f"📚 {collection_name}"):
                st.write(collection_data["description"])
                collection_books = [book for book in st.session_state.users[st.session_state.current_user]['books'] if collection_name in book.get("collections", [])]
                if collection_books:
                    for book in collection_books:
                        st.markdown('<div class="book-card">', unsafe_allow_html=True)
                        st.write(f"- {book['title']} by {book['author']}")
                        st.markdown('</div>', unsafe_allow_html=True)
                else:
                    st.info("No books in this collection yet.")

    # View Library Page
    elif page == "View Library":
        st.title("📚 Your Library")
        
        # Search and filter
        search_query = st.text_input("Search books")
        status_filter = st.selectbox("Filter by status", ["All", "Read", "Unread", "Reading"])
        collection_filter = st.selectbox("Filter by collection", ["All"] + list(st.session_state.users[st.session_state.current_user]['collections'].keys()))
        
        filtered_books = st.session_state.users[st.session_state.current_user]['books']
        if search_query:
            filtered_books = [book for book in filtered_books 
                            if search_query.lower() in book['title'].lower() 
                            or search_query.lower() in book['author'].lower()]
        if status_filter != "All":
            filtered_books = [book for book in filtered_books if book['status'] == status_filter]
        if collection_filter != "All":
            filtered_books = [book for book in filtered_books if collection_filter in book.get('collections', [])]
        
        if filtered_books:
            for idx, book in enumerate(filtered_books):
                with st.container():
                    st.markdown('<div class="book-card">', unsafe_allow_html=True)
                    col1, col2, col3 = st.columns([1, 3, 1])
                    with col1:
                        if book.get('cover_image'):
                            st.image(f"data:image/png;base64,{book['cover_image']}", width=150)
                        elif book.get('cover_url'):
                            st.image(book['cover_url'], width=150)
                        else:
                            st.image("https://via.placeholder.com/150x200?text=No+Cover", width=150)
                    with col2:
                        st.write(f"**{book['title']}**")
                        st.write(f"by {book['author']}")
                        st.write(f"Status: {book['status']}")
                        st.write(f"Rating: {'⭐' * book['rating']}")
                        if book.get('collections'):
                            st.write(f"Collections: {', '.join(book['collections'])}")
                    with col3:
                        st.write("")  # Spacer
                        st.write("")  # Spacer
                        if st.button("🗑️ Delete", key=f"delete_{book['title']}_{idx}_{book.get('isbn', '')}"):
                            st.session_state.users[st.session_state.current_user]['books'].remove(book)
                            save_users()
                            st.rerun()
                    st.markdown('</div>', unsafe_allow_html=True)
        else:
            st.info("No books found matching your criteria.")

    # Statistics Page
    elif page == "Statistics":
        st.title("📊 Library Statistics")
        
        if st.session_state.users[st.session_state.current_user]['books']:
            df = pd.DataFrame(st.session_state.users[st.session_state.current_user]['books'])
            
            col1, col2 = st.columns(2)
            
            with col1:
                # Status distribution with enhanced styling
                status_counts = df['status'].value_counts()
                fig1 = px.pie(
                    values=status_counts.values,
                    names=status_counts.index,
                    title="Book Status Distribution",
                    template="plotly_dark",
                    color_discrete_sequence=['#00b4d8', '#0077b6', '#90e0ef']
                )
                fig1.update_layout(
                    paper_bgcolor='rgba(0,0,0,0)',
                    plot_bgcolor='rgba(0,0,0,0)'
                )
                st.plotly_chart(fig1, use_container_width=True)
            
            with col2:
                # Rating distribution with enhanced styling
                rating_counts = df['rating'].value_counts().sort_index()
                fig2 = px.bar(
                    x=rating_counts.index,
                    y=rating_counts.values,
                    title="Rating Distribution",
                    template="plotly_dark",
                    labels={'x': 'Rating', 'y': 'Count'},
                    color_discrete_sequence=['#00b4d8']
                )
                fig2.update_layout(
                    paper_bgcolor='rgba(0,0,0,0)',
                    plot_bgcolor='rgba(0,0,0,0)'
                )
                st.plotly_chart(fig2, use_container_width=True)
            
            # Monthly additions with enhanced styling
            df['date_added'] = pd.to_datetime(df['date_added'])
            monthly_additions = df.groupby(df['date_added'].dt.to_period('M')).size()
            fig3 = px.line(
                x=monthly_additions.index.astype(str),
                y=monthly_additions.values,
                title="Monthly Book Additions",
                template="plotly_dark",
                labels={'x': 'Month', 'y': 'Number of Books'},
                color_discrete_sequence=['#00b4d8']
            )
            fig3.update_layout(
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(0,0,0,0)'
            )
            st.plotly_chart(fig3, use_container_width=True)
        else:
            st.info("No statistics available. Add some books to see your library statistics!")

# Main application flow
if not st.session_state.authenticated:
    auth_page()
else:
    if check_auth():
        main_app()

# Enhanced Custom CSS for futuristic style
st.markdown("""
    <style>
    /* Main background with enhanced animated gradient and particles */
    .main {
        background: linear-gradient(-45deg, 
            #0f0c29, 
            #302b63, 
            #24243e, 
            #1a1a2e,
            #0f0c29,
            #302b63);
        background-size: 400% 400%;
        animation: gradient 20s ease infinite;
        color: #ffffff;
        position: relative;
        overflow: hidden;
    }
    
    /* Particle animation layer */
    .main::before {
        content: '';
        position: absolute;
        top: 0;
        left: 0;
        right: 0;
        bottom: 0;
        background: radial-gradient(circle at 50% 50%, 
            rgba(0, 180, 216, 0.1) 0%,
            transparent 50%);
        animation: pulse 8s ease-in-out infinite;
        pointer-events: none;
    }
    
    /* Floating particles */
    .main::after {
        content: '';
        position: absolute;
        top: 0;
        left: 0;
        right: 0;
        bottom: 0;
        background-image: 
            radial-gradient(2px 2px at 20px 30px, #00b4d8, rgba(0, 180, 216, 0)),
            radial-gradient(2px 2px at 40px 70px, #00b4d8, rgba(0, 180, 216, 0)),
            radial-gradient(2px 2px at 50px 160px, #00b4d8, rgba(0, 180, 216, 0)),
            radial-gradient(2px 2px at 90px 40px, #00b4d8, rgba(0, 180, 216, 0)),
            radial-gradient(2px 2px at 130px 80px, #00b4d8, rgba(0, 180, 216, 0)),
            radial-gradient(2px 2px at 160px 120px, #00b4d8, rgba(0, 180, 216, 0));
        background-repeat: repeat;
        background-size: 200px 200px;
        animation: float 20s linear infinite;
        opacity: 0.3;
        pointer-events: none;
    }
    
    @keyframes gradient {
        0% {
            background-position: 0% 50%;
        }
        50% {
            background-position: 100% 50%;
        }
        100% {
            background-position: 0% 50%;
        }
    }
    
    @keyframes pulse {
        0% {
            transform: scale(1);
            opacity: 0.5;
        }
        50% {
            transform: scale(1.2);
            opacity: 0.8;
        }
        100% {
            transform: scale(1);
            opacity: 0.5;
        }
    }
    
    @keyframes float {
        0% {
            transform: translateY(0px);
        }
        100% {
            transform: translateY(-200px);
        }
    }
    
    /* Interactive hover effects */
    .element-container:hover {
        transform: translateY(-5px) scale(1.02);
        box-shadow: 0 10px 20px rgba(0, 180, 216, 0.3);
        border: 1px solid rgba(0, 180, 216, 0.5);
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
    }
    
    /* Enhanced button animations */
    .stButton>button {
        background: linear-gradient(45deg, #00b4d8, #0077b6);
        color: white;
        border: none;
        border-radius: 10px;
        padding: 12px 24px;
        font-weight: bold;
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
        box-shadow: 0 4px 15px rgba(0, 180, 216, 0.3);
        position: relative;
        overflow: hidden;
    }
    
    .stButton>button:hover {
        transform: scale(1.05) translateY(-2px);
        box-shadow: 0 0 20px #00b4d8;
    }
    
    .stButton>button::before {
        content: '';
        position: absolute;
        top: -50%;
        left: -50%;
        width: 200%;
        height: 200%;
        background: linear-gradient(
            45deg,
            transparent,
            rgba(255, 255, 255, 0.1),
            transparent
        );
        transform: rotate(45deg);
        transition: 0.5s;
    }
    
    .stButton>button:hover::before {
        animation: shine 1.5s infinite;
    }
    
    /* Enhanced card styling with 3D effect */
    .book-card {
        background: rgba(255, 255, 255, 0.1);
        border-radius: 15px;
        padding: 20px;
        margin: 10px 0;
        border: 1px solid rgba(255, 255, 255, 0.2);
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
        backdrop-filter: blur(10px);
        box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1);
        transform-style: preserve-3d;
        perspective: 1000px;
    }
    
    .book-card:hover {
        transform: translateY(-5px) rotateX(5deg);
        box-shadow: 0 10px 20px rgba(0, 180, 216, 0.3);
        border: 1px solid rgba(0, 180, 216, 0.5);
    }
    
    /* Enhanced input fields with focus effects */
    .stTextInput>div>div>input,
    .stSelectbox>div>div>select {
        background-color: rgba(255, 255, 255, 0.1);
        color: white;
        border: 1px solid #00b4d8;
        border-radius: 10px;
        padding: 8px 12px;
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
        box-shadow: 0 0 10px rgba(0, 180, 216, 0.1);
    }
    
    .stTextInput>div>div>input:focus,
    .stSelectbox>div>div>select:focus {
        box-shadow: 0 0 20px #00b4d8;
        border-color: #00b4d8;
        background-color: rgba(255, 255, 255, 0.15);
        transform: scale(1.02);
    }
    
    /* Enhanced title styling with multiple effects */
    h1 {
        color: #00b4d8;
        text-shadow: 0 0 10px rgba(0, 180, 216, 0.5),
                     0 0 20px rgba(0, 180, 216, 0.3),
                     0 0 30px rgba(0, 180, 216, 0.2);
        font-weight: bold;
        letter-spacing: 1px;
        position: relative;
        animation: titleGlow 3s ease-in-out infinite;
    }
    
    @keyframes titleGlow {
        0%, 100% {
            text-shadow: 0 0 10px rgba(0, 180, 216, 0.5),
                         0 0 20px rgba(0, 180, 216, 0.3),
                         0 0 30px rgba(0, 180, 216, 0.2);
        }
        50% {
            text-shadow: 0 0 20px rgba(0, 180, 216, 0.7),
                         0 0 30px rgba(0, 180, 216, 0.5),
                         0 0 40px rgba(0, 180, 216, 0.3);
        }
    }
    
    /* Enhanced scrollbar with gradient effect */
    ::-webkit-scrollbar {
        width: 8px;
    }
    
    ::-webkit-scrollbar-track {
        background: rgba(255, 255, 255, 0.1);
    }
    
    ::-webkit-scrollbar-thumb {
        background: linear-gradient(45deg, #00b4d8, #0077b6);
        border-radius: 4px;
        box-shadow: 0 0 10px rgba(0, 180, 216, 0.5);
    }
    
    /* Enhanced success and info messages */
    .stAlert {
        background: rgba(40, 167, 69, 0.2);
        border: 1px solid rgba(40, 167, 69, 0.3);
        border-radius: 10px;
        backdrop-filter: blur(10px);
        box-shadow: 0 0 20px rgba(40, 167, 69, 0.2);
        animation: alertPulse 2s ease-in-out infinite;
    }
    
    @keyframes alertPulse {
        0%, 100% {
            box-shadow: 0 0 20px rgba(40, 167, 69, 0.2);
        }
        50% {
            box-shadow: 0 0 30px rgba(40, 167, 69, 0.4);
        }
    }
    </style>
    """, unsafe_allow_html=True)

# Function to load data
def load_data():
    try:
        # Check if current user exists in users dictionary
        if st.session_state.current_user not in st.session_state.users:
            st.session_state.users[st.session_state.current_user] = {
                'books': [],
                'collections': {}
            }
            save_users()
            return

        # Load data from file if it exists
        if os.path.exists('library_data.json'):
            with open('library_data.json', 'r') as f:
                data = json.load(f)
                # Initialize books and collections if they don't exist
                if 'books' not in st.session_state.users[st.session_state.current_user]:
                    st.session_state.users[st.session_state.current_user]['books'] = []
                if 'collections' not in st.session_state.users[st.session_state.current_user]:
                    st.session_state.users[st.session_state.current_user]['collections'] = {}
                
                # Update user data with loaded data
                st.session_state.users[st.session_state.current_user]['books'] = data.get('books', [])
                st.session_state.users[st.session_state.current_user]['collections'] = data.get('collections', {})
        else:
            # Initialize empty data structure if file doesn't exist
            st.session_state.users[st.session_state.current_user]['books'] = []
            st.session_state.users[st.session_state.current_user]['collections'] = {}
            save_users()
    except Exception as e:
        st.error(f"Error loading data: {str(e)}")
        # Initialize empty data structure on error
        st.session_state.users[st.session_state.current_user]['books'] = []
        st.session_state.users[st.session_state.current_user]['collections'] = {}
        save_users()

# Function to save data
def save_data():
    try:
        if st.session_state.current_user and st.session_state.current_user in st.session_state.users:
            data = {
                'books': st.session_state.users[st.session_state.current_user]['books'],
                'collections': st.session_state.users[st.session_state.current_user]['collections']
            }
            with open('library_data.json', 'w') as f:
                json.dump(data, f)
    except Exception as e:
        st.error(f"Error saving data: {str(e)}")

# Load data on startup
if st.session_state.authenticated and st.session_state.current_user:
    load_data()