from django.test import Client
from django.contrib.auth.models import User

c = Client()
user = User.objects.filter(username='manager').first() or User.objects.filter(username='adham').first() or User.objects.first()
if not user:
    print('no user')
else:
    c.force_login(user)
    from basket.models import Order
    o = Order.objects.order_by('-id').first()
    if not o:
        print('no order to test')
    else:
        print('Testing update_status for order', o.id, 'current', o.status)
        resp = c.post('/manager/orders/', {'action':'update_status','order_id':str(o.id),'status':'paid'}, HTTP_HOST='localhost')
        print('update resp', resp.status_code)
        o.refresh_from_db()
        print('new status', o.status)
        # now test delete
        resp2 = c.post('/manager/orders/', {'action':'delete','order_id':str(o.id)}, HTTP_HOST='localhost')
        print('delete resp', resp2.status_code)
        from django.db import connection
        cur = connection.cursor()
        cur.execute('SELECT COUNT(*) FROM basket_order WHERE id=?', (o.id,))
        print('exists after delete:', cur.fetchone()[0])
