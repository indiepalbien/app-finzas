web: cd backend && python manage.py migrate && python manage.py collectstatic --noinput && gunicorn --worker-tmp-dir /dev/shm misfinanzas.wsgi:application
