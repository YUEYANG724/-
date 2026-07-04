// ========== State ==========
let allPhotos = {};          // { category: [photo, ...] }
let flatPhotos = [];         // [{ url, filename, category }, ...]
let currentCategory = 'all';
let currentIndex = 0;

const galleryEl = document.getElementById('gallery');
const lightbox = document.getElementById('lightbox');
const lightboxImg = document.getElementById('lightboxImage');
const lightboxCounter = document.getElementById('lightboxCounter');

// ========== Fetch & Init ==========
async function init() {
  try {
    const res = await fetch('/api/categories');
    allPhotos = await res.json();

    // Build flat array
    flatPhotos = [];
    for (const [cat, photos] of Object.entries(allPhotos)) {
      for (const p of photos) {
        flatPhotos.push({ ...p, category: cat });
      }
    }

    renderGallery('all');
    bindCategoryButtons();
    bindLightbox();
  } catch (err) {
    galleryEl.innerHTML = '<div class="empty-state">加载失败，请检查网络后重试</div>';
  }
}

// ========== Render ==========
function renderGallery(category) {
  currentCategory = category;

  let photos;
  if (category === 'all') {
    photos = flatPhotos;
  } else {
    photos = (allPhotos[category] || []).map(p => ({ ...p, category }));
  }

  if (photos.length === 0) {
    galleryEl.innerHTML = '<div class="empty-state">暂无照片</div>';
    return;
  }

  galleryEl.innerHTML = photos.map((photo, idx) => `
    <div class="gallery-item" data-index="${idx}" data-category="${category}">
      <img
        data-src="${photo.url}"
        src="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='1' height='1'%3E%3C/svg%3E"
        alt="${photo.filename}"
        class="loading"
        loading="lazy"
      />
      <span class="category-tag">${photo.category}</span>
    </div>
  `).join('');

  // Lazy load images
  observeImages();

  // Click to open lightbox
  document.querySelectorAll('.gallery-item').forEach((el, idx) => {
    el.addEventListener('click', () => openLightbox(idx, category));
  });
}

// ========== Lazy Loading with Intersection Observer ==========
let imageObserver;
function observeImages() {
  if (imageObserver) imageObserver.disconnect();
  imageObserver = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
      if (entry.isIntersecting) {
        const img = entry.target;
        const src = img.dataset.src;
        if (src) {
          const temp = new Image();
          temp.onload = () => {
            img.src = src;
            img.classList.remove('loading');
            img.classList.add('loaded');
          };
          temp.onerror = () => {
            img.classList.remove('loading');
            img.src = "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='400' height='300'%3E%3Crect fill='%23eae5df' width='400' height='300'/%3E%3Ctext x='200' y='150' text-anchor='middle' fill='%23999' font-size='14'%3E加载失败%3C/text%3E%3C/svg%3E";
          };
          temp.src = src;
        }
        imageObserver.unobserve(img);
      }
    });
  }, { rootMargin: '200px' });

  document.querySelectorAll('.gallery-item img.loading').forEach(img => {
    imageObserver.observe(img);
  });
}

// ========== Category Buttons ==========
function bindCategoryButtons() {
  document.querySelectorAll('.category-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      document.querySelectorAll('.category-btn').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      const cat = btn.dataset.category;
      renderGallery(cat);
    });
  });
}

// ========== Lightbox ==========
function openLightbox(index, category) {
  let photos;
  if (category === 'all') {
    photos = flatPhotos;
  } else {
    photos = (allPhotos[category] || []).map(p => ({ ...p, category }));
  }

  currentIndex = index;
  showLightboxImage(photos, index);
  lightbox.classList.add('open');
  document.body.style.overflow = 'hidden';

  // Attach navigation
  const prevBtn = document.getElementById('lightboxPrev');
  const nextBtn = document.getElementById('lightboxNext');

  const goPrev = () => {
    if (photos.length === 0) return;
    currentIndex = (currentIndex - 1 + photos.length) % photos.length;
    showLightboxImage(photos, currentIndex);
  };

  const goNext = () => {
    if (photos.length === 0) return;
    currentIndex = (currentIndex + 1) % photos.length;
    showLightboxImage(photos, currentIndex);
  };

  prevBtn.onclick = goPrev;
  nextBtn.onclick = goNext;

  // Keyboard
  const keyHandler = (e) => {
    if (e.key === 'Escape') closeLightbox();
    if (e.key === 'ArrowLeft') goPrev();
    if (e.key === 'ArrowRight') goNext();
  };
  document.addEventListener('keydown', keyHandler);

  // Touch swipe
  let startX = 0, startY = 0;
  const touchStart = (e) => {
    startX = e.touches[0].clientX;
    startY = e.touches[0].clientY;
  };
  const touchEnd = (e) => {
    const dx = e.changedTouches[0].clientX - startX;
    const dy = e.changedTouches[0].clientY - startY;
    if (Math.abs(dx) > Math.abs(dy) && Math.abs(dx) > 50) {
      if (dx > 0) goPrev();
      else goNext();
    }
  };
  lightbox.addEventListener('touchstart', touchStart);
  lightbox.addEventListener('touchend', touchEnd);

  // Cleanup on close
  const cleanup = () => {
    document.removeEventListener('keydown', keyHandler);
    lightbox.removeEventListener('touchstart', touchStart);
    lightbox.removeEventListener('touchend', touchEnd);
    document.getElementById('lightboxClose').removeEventListener('click', cleanup);
    lightbox.removeEventListener('click', backdropClick);
  };

  const closeHandler = () => {
    cleanup();
    closeLightbox();
  };

  const backdropClick = (e) => {
    if (e.target === lightbox) {
      cleanup();
      closeLightbox();
    }
  };

  document.getElementById('lightboxClose').addEventListener('click', closeHandler);
  lightbox.addEventListener('click', backdropClick);

  // Store cleanup reference on lightbox
  lightbox._cleanup = closeHandler;
}

function showLightboxImage(photos, index) {
  const photo = photos[index];
  lightboxImg.src = photo.url;
  lightboxImg.alt = photo.filename;
  lightboxCounter.textContent = `${index + 1} / ${photos.length}`;
}

function closeLightbox() {
  lightbox.classList.remove('open');
  document.body.style.overflow = '';
  lightboxImg.src = '';
}

// ========== Start ==========
init();
