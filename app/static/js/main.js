/**
 * Основной JS-файл для UI маркетплейса.
 *
 * - Обновляет навигацию (показывает/скрывает ссылки в зависимости от JWT)
 * - Добавляет кнопку "Выйти" при наличии токена
 */

document.addEventListener('DOMContentLoaded', () => {
    const token = localStorage.getItem('token');
    const authLinks = document.getElementById('authLinks');

    if (token) {
        // Получаем имя пользователя для отображения
        fetch('/api/v1/auth/me', {
            headers: { 'Authorization': `Bearer ${token}` }
        })
        .then(res => {
            if (!res.ok) throw new Error('Unauthorized');
            return res.json();
        })
        .then(user => {
            if (authLinks) {
                authLinks.innerHTML = `
                    <a href="/profile">${user.username}</a>
                    <a href="#" id="logoutBtn">Выйти</a>
                `;
                document.getElementById('logoutBtn').addEventListener('click', (e) => {
                    e.preventDefault();
                    localStorage.removeItem('token');
                    window.location.href = '/';
                });
            }
        })
        .catch(() => {
            localStorage.removeItem('token');
            if (authLinks) {
                authLinks.innerHTML = `<a href="/login">Войти</a><a href="/register">Регистрация</a>`;
            }
        });
    } else {
        if (authLinks) {
            authLinks.innerHTML = `<a href="/login">Войти</a><a href="/register">Регистрация</a>`;
        }
    }
});
