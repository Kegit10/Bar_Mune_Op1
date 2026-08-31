const router = {
    navigate(page) {
        window.location.href = `/frontend/pages/${page}.html`;
    },
    
    isActive(page) {
        return window.location.pathname.includes(page);
    }
};

window.router = router;
