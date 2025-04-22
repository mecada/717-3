from django.conf import settings
from io import BytesIO
from django.http import HttpResponse, JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.core.validators import validate_email
from django.core.exceptions import ValidationError
import random
from django.db.utils import IntegrityError
from django.urls import reverse
from .models import *
import datetime
from django.core.mail import send_mail
from .utils import *
import re
from django.utils.timezone import now
from reportlab.pdfgen import canvas
from django.core.mail import EmailMessage
import imghdr
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.utils import ImageReader
import os
from django.contrib.sessions.models import Session
from reportlab.lib.units import cm
from io import BytesIO
import uuid
from reportlab.lib.pagesizes import letter
from django.utils.timezone import now
from django.db import transaction

# Vista de inicio
def inicio(request):

    p = list(Producto.objects.all())
    destacados = random.sample(p, min(len(p), 3))
    contexto = {
        "data": destacados
    }
    return render(request, "index.html", contexto)


# Vista de contacto

def contacto(request):
    if request.method == "POST":
        auth = request.session.get("auth")

        if auth: 
            nombre = f"{auth['nombre']} {auth['apellido']}"
            email = auth["correo"]
        else:
            nombre = request.POST.get("txtNombre", "").strip()
            email = request.POST.get("txtEmail", "").strip()

        contenido = request.POST.get("txtMensaje", "").strip()

        if not nombre or not email or not contenido:
            messages.error(request,"Todos los campos son obligatorios.")
            return render(request, "contacto.html")

        if not re.match(r'^[a-zA-ZáéíóúÁÉÍÓÚñÑ ]+$', nombre):
            messages.error(request, "El nombre solo puede contener letras y espacios.")
            return render(request, "contacto.html")

        else:

            try:
                validate_email(email)
            except ValidationError:
                messages.error(request, "El correo electrónico no tiene un formato válido.")
                return render(request, "register.html")    

            asunto = f"Mensaje de contacto de {nombre}"
            cuerpo = f"{contenido}\n\nEmail de contacto: {email}"

            email_desde = settings.EMAIL_HOST_USER
            email_para = ["717days@gmail.com"]

            correo = EmailMessage(
                subject=asunto,
                body=cuerpo,
                from_email=email_desde,
                to=email_para,
            )

            try:
                correo.send()
                messages.success(request, "Mensaje enviado con éxito. Nos pondremos en contacto contigo pronto.")
            except Exception as e:
                messages.error(request, f"Error al enviar el mensaje: {str(e)}")

    return render(request, "contacto.html") 

#Vista de legal
def legal(request):
    return render(request, 'legal.html')


def detalles(request, producto_id):
    producto = get_object_or_404(Producto, id=producto_id)

    if request.method == 'POST':
        talla = request.POST.get('talla')  

        
        if talla:
            carrito = request.session.get('carrito', [])

            item_en_carrito = next((item for item in carrito if item['id'] == producto.id and item['talla'] == talla), None)

            if item_en_carrito:
                item_en_carrito['cantidad'] += 1
            else:
                carrito.append({
                    'id': producto.id,
                    'nombre': producto.nombre,
                    'precio': producto.precio,
                    'talla': talla,
                    'cantidad': 1,
                    'foto': producto.foto.url,
                })

            request.session['carrito'] = carrito

            return redirect('ver_carrito')
        else:
            return render(request, 'detalles.html', {'producto': producto, 'error': 'Por favor, selecciona una talla.'})

    return render(request, 'detalles.html', {'producto': producto})


def validar_telefono(telefono):
    return re.match(r'^\d{7,15}$', telefono) is not None
#CRUD de perfil

# Vista de reigstro

def register(request):
    verificar = request.session.get("auth", False)
    if verificar:
        return redirect("inicio")
    else:
        
        if request.method == "POST":
            request.session["datos"] = request.POST
            nombre = request.POST.get("nombre")
            apellido = request.POST.get("apellido")
            correo = request.POST.get("correo")
            password = request.POST.get("password")
            confirm_password = request.POST.get("confirm_password")
            telefono = request.POST.get("telefono")
            direccion = request.POST.get("direccion")
            fecha_nac = request.POST.get("fecha_nac")
            genero = request.POST.get("genero")
            cedula = request.POST.get("cedula")
            
            try:
                validate_email(correo)
            except ValidationError:
                messages.error(request, "El correo electrónico no tiene un formato válido.")
                return render(request, "register.html")

            if Usuario.objects.filter(correo=correo).exists():
                messages.error(request, "El correo electrónico ya está registrado.")
                return render(request, "register.html")
            else:
                try:
                    fecha_nac = datetime.datetime.strptime(fecha_nac, "%Y-%m-%d").date()
                    if fecha_nac >= datetime.date.today():
                        messages.error(request, "La fecha de nacimiento debe ser anterior a hoy.")
                        return render(request, "register.html")                  
                    if not re.match(r'^[a-zA-ZáéíóúÁÉÍÓÚñÑ ]+$', nombre):
                        messages.error(request, "El nombre solo puede contener letras y espacios.")
                        return render(request, "register.html")
                    if not re.match(r'^[a-zA-ZáéíóúÁÉÍÓÚñÑ ]+$', apellido):
                        messages.error(request, "El apellido solo puede contener letras y espacios.")
                        return render(request, "register.html")
                    if not validar_telefono(telefono):
                        messages.error(request, "El teléfono debe contener entre 7 y 15 dígitos numéricos.")
                        return render(request, "register.html")
                    if not cedula.isdigit():
                        messages.error(request, "La cédula solo debe contener números.")
                        return render(request, "register.html")
                    if password != confirm_password:
                        messages.error(request, "Las contraseñas no coinciden.")
                        return render(request, "register.html")
                    
                    q = Usuario(
                        cedula=cedula,
                        nombre=nombre,
                        apellido=apellido,
                        telefono=telefono,
                        direccion=direccion,
                        correo=correo,
                        password=hash_password(password),
                        fecha_nac=fecha_nac,
                        genero=genero,
                        rol=3
                    )
                    q.save()
                    request.session["datos"]= None
                    messages.success(request, "Registro exitoso. Ahora puedes iniciar sesión.")
                    return redirect('login')

                except ValueError:
                    messages.error(request, "Formato de fecha inválido. Use YYYY-MM-DD.")
                    return render(request, "register.html")


        return render(request, "register.html", {})

# Vista de login
def login(request):  
    verificar = request.session.get("auth", False)
    if verificar:
        return redirect("inicio")
    else:
        if request.method == "POST":
            correo = request.POST.get("correo")
            password = request.POST.get("password")
            try:
                q = Usuario.objects.get(correo=correo)
                if verify_password(password, q.password):
                    # Crear variable de sesión ========
                    request.session["auth"] = {
                        "id": q.id,
                    "nombre": q.nombre,
                    "apellido": q.apellido,
                    "correo": q.correo,
                    "telefono": q.telefono,
                    "direccion": q.direccion,
                    "rol": q.rol,
                    "nombre_rol": q.get_rol_display(),
                    }
                    return redirect("inicio")
                else:
                    raise Usuario.DoesNotExist()

            except Usuario.DoesNotExist:
                messages.warning(request, "Usuario o contraseña no válidos..")
                request.session["auth"] = None
            except Exception as e:
                messages.error(request, f"Error: {e}")
                request.session["auth"] = None
            return redirect("login")
        else:
            verificar = request.session.get("auth", False)

            if verificar:
                return redirect("inicio")
            else:
                return render(request, "login.html")

    
    

# Vista de cerrar sesion

def logout(request):
    verificar = request.session.get("auth", False)
    if verificar:
        try:
            del request.session["auth"]
            return redirect("inicio")
        except Exception as e:
            messages.info(request, "No se pudo cerrar sesión, intente de nuevo")
            return redirect("perfil")
    else:
        pass
    request



def editar_perfil(request):
    verificar = request.session.get("auth", False)
    if verificar:
        pass
    else:
        messages.info(request, "Usted no tiene permisos para éste módulo...")
        return redirect("inicio")
    if request.method == "POST":
        try:
            user_id = request.session.get("auth", {}).get("id")
            if not user_id:
                messages.error(request, "Usuario no autenticado.")
                return redirect("login")
            
            usuario = Usuario.objects.get(pk=user_id)
            
            nombre = request.POST.get("nombre").strip()
            apellido = request.POST.get("apellido").strip()
            telefono = request.POST.get("telefono").strip()
            direccion = request.POST.get("direccion").strip()
            correo = request.POST.get("correo").strip()
            
            if not re.match(r'^[a-zA-ZáéíóúÁÉÍÓÚñÑ ]+$', nombre):
                messages.error(request, "El nombre solo puede contener letras y espacios.")
                return redirect("editar_perfil")
            
            if not re.match(r'^[a-zA-ZáéíóúÁÉÍÓÚñÑ ]+$', apellido):
                messages.error(request, "El apellido solo puede contener letras y espacios.")
                return redirect("editar_perfil")
            
            if not validar_telefono(telefono):
                messages.error(request, "El teléfono debe contener entre 7 y 15 dígitos numéricos.")
                return redirect("editar_perfil")
            
            if not re.match(r'^[a-zA-Z0-9áéíóúÁÉÍÓÚñÑ ,.]+$', direccion):
                messages.error(request, "La dirección contiene caracteres no permitidos.")
                return redirect("editar_perfil")
            
            if Usuario.objects.exclude(pk=user_id).filter(correo=correo).exists():
                messages.error(request, "Este correo ya está en uso por otro usuario.")
                return redirect("editar_perfil")
            
            usuario.nombre = nombre
            usuario.apellido = apellido
            usuario.telefono = telefono
            usuario.direccion = direccion
            usuario.correo = correo
            usuario.save()
            request.session["auth"] = {
                        "id": usuario.id,
                    "nombre": usuario.nombre,
                    "apellido": usuario.apellido,
                    "correo": usuario.correo,
                    "telefono": usuario.telefono,
                    "direccion": usuario.direccion,
                    "rol": usuario.rol,
                    "nombre_rol": usuario.get_rol_display(),
                    }
            
            messages.success(request, "Perfil actualizado correctamente.")
            return redirect("perfil")
        except Exception as e:
            messages.error(request, f"Error: {e}")
            return redirect("editar_perfil")
    else:
        return render(request, "editar-perfil.html")
def cambiar_password(request):
    verificar = request.session.get("auth", False)
    if verificar:
        if request.method == "POST":
            clave_actual = request.POST.get("clave_actual")
            nueva = request.POST.get("nueva")
            repite_nueva = request.POST.get("repite_nueva")
            logueado = request.session.get("auth", False)
            clave_actual = hash_password(clave_actual)
            q = Usuario.objects.get(pk=logueado["id"])
            if clave_actual == q.password:
                if nueva == repite_nueva:
                    q.password = hash_password(nueva)
                    q.save()
                    messages.success(request, "Contraseña actualizada con exito")

                else:
                    messages.success(request, "Contraseñas nuevas no coinciden")
            else:
                messages.success(request, "La contraseña no concuerda")
                
                
            return redirect("cambiar_clave")
            
        else:
            return render(request, "usuarios/cambiar_clave.html")
    else:
        pass
        
    


# Vista de perfil
def perfil(request):
    verificar = request.session.get("auth", False)
    if verificar:
        pass
    else:
        messages.info(request, "Usted no tiene permisos para éste módulo...")
        return redirect("inicio")
    
    return render(request, 'perfil.html')

# Vista de pedidos
def pedidos(request):
    verificar = request.session.get("auth", False)
    if verificar:
        if verificar["rol"] !=3 :
            return redirect("inicio")
        else:
            return render(request, 'pedidos.html')    
    else:    
        return redirect("inicio")


# Función para eliminar producto del carrito
def eliminar_del_carrito(request, producto_id, talla):
    carrito = request.session.get('carrito', {})
    clave_producto = f"{producto_id}-{talla}"

    if clave_producto in carrito:
        del carrito[clave_producto]
        request.session['carrito'] = carrito
        messages.success(request, "Producto eliminado del carrito con éxito.")
    else:
        messages.error(request, "El producto no está en el carrito.")

    return redirect('cart')



# Función para agregar al carrito
def agregar_al_carrito(request, producto_id):
    producto = get_object_or_404(Producto, id=producto_id)
    talla = request.POST.get('talla', '').strip()
    if request.method == "POST":
        try:
            cantidad = int(request.POST.get('cantidad', 1))
            if cantidad < 1:
                raise ValueError
        except ValueError:
            messages.error(request, "La cantidad debe ser un número entero positivo.")
            return redirect(request.META.get('HTTP_REFERER', 'inicio'))

        if not talla:
            messages.error(request, "Debe seleccionar una talla antes de agregar al carrito.")
            return redirect(request.META.get('HTTP_REFERER', 'inicio'))

        carrito = request.session.get('carrito', {})
        clave_producto = f"{producto_id}-{talla}"

        # Calcular cuántas unidades ya hay en el carrito para este producto (sin importar talla)
        total_en_carrito = sum(
            item['cantidad'] for key, item in carrito.items()
            if key.startswith(f"{producto_id}-")
        )

        if total_en_carrito + cantidad > producto.cantidad:
            disponible = producto.cantidad - total_en_carrito
            messages.error(request, f"Solo hay {disponible} unidades disponibles para este producto.")
            return redirect(request.META.get('HTTP_REFERER', 'inicio'))

        if clave_producto in carrito:
            carrito[clave_producto]['cantidad'] += cantidad
        else:
            carrito[clave_producto] = {
                'nombre': producto.nombre,
                'precio': producto.precio,
                'foto': producto.foto.url if producto.foto else '',
                'cantidad': cantidad,
                'talla': talla
            }

        request.session['carrito'] = carrito
        messages.success(request, "Producto agregado al carrito con éxito.")
        return redirect(request.META.get('HTTP_REFERER', 'inicio'))
    else:
        return redirect("productos")




#Actualizar Cantidad

def actualizar_cantidad(request, producto_id, talla, accion):
    carrito = request.session.get('carrito', {})
    clave_producto = f"{producto_id}-{talla}"

    if clave_producto in carrito:
        producto = get_object_or_404(Producto, id=producto_id)
        cantidad_actual = carrito[clave_producto]['cantidad']

        # Sumar todas las cantidades de este producto en el carrito
        total_en_carrito = sum(
            item['cantidad'] for key, item in carrito.items()
            if key.startswith(f"{producto_id}-")
        )

        if accion == "incrementar":
            if total_en_carrito < producto.cantidad:
                carrito[clave_producto]['cantidad'] += 1
            else:
                messages.error(request, "No puedes agregar más unidades de las disponibles en stock.")
        elif accion == "decrementar":
            if cantidad_actual > 1:
                carrito[clave_producto]['cantidad'] -= 1
            else:
                del carrito[clave_producto]

    request.session['carrito'] = carrito
    return redirect('cart')



#Vaciar carrito

def vaciar_carrito(request):
    request.session['carrito'] = {}  
    request.session.modified = True  
    return redirect('cart')



#Funcion del carrito despues de iniciar secion
def fusionar_carrito(request):
    verificar = request.session.get("auth", False)

    if verificar:
        carrito_sesion = request.session.get('carrito', {})
        carrito_usuario = request.user.carrito.all()

        for producto_id, tallas in carrito_sesion.items():
            for talla, cantidad in tallas.items():
                producto = Producto.objects.get(id=producto_id)

                if not carrito_usuario.filter(producto=producto, talla=talla).exists():
                    request.user.carrito.create(producto=producto, talla=talla, cantidad=cantidad)

        del request.session['carrito']

#Funcion para eliminar productos que se queden sin stock
def verificar_stock(request):
    verificar = request.session.get("auth", False)

    carrito = request.session.get('carrito', {})

    for producto_id, tallas in list(carrito.items()):
        producto = Producto.objects.get(id=producto_id)
        if producto.cantidad == 0:
            del carrito[producto_id]
    
    request.session['carrito'] = carrito
    messages.info(request, "Se eliminaron productos sin stock del carrito.")

    return redirect('ver_carrito')


# Función para ver el carrito
def cart(request):
    carrito = request.session.get('carrito', {})
    carrito_items = []
    total = 0

    print("Contenido del carrito en la sesión:", carrito)  # Depuración

    if isinstance(carrito, dict):
        for clave_producto, item in carrito.items():
            print("Procesando item:", item)  # Depuración

            nombre = item.get('nombre', 'Producto sin nombre')
            precio = item.get('precio', 0)
            foto = item.get('foto', '')
            cantidad = item.get('cantidad', 1)
            talla = item.get('talla', 'N/A')

            subtotal = precio * cantidad
            total += subtotal

            carrito_items.append({
                'id': clave_producto.split('-')[0],
                'nombre': nombre,
                'precio': precio,
                'foto': foto,
                'cantidad': cantidad,
                'talla': talla,
                'subtotal': subtotal
            })
    else:
        print("⚠️ El carrito no es un diccionario. Valor:", carrito)


    return render(request, 'cart.html', {'carrito_items': carrito_items, 'total': total})


#CRUD para Usuarios //////////////////////////////////////////////////////////////////////////////////////////////////////////

# Vista para ver usuarios
def listar_usuarios(request):
    verificar = request.session.get("auth", False)
    if verificar:
        if verificar["rol"] != 3 :
            u = Usuario.objects.all()
            contexto = {
                "data": u
                }
            return render(request, "usuarios/listar_usuarios.html", contexto)
        else:
            messages.info(request, "Usted no tiene permisos para éste módulo...")
        return redirect("inicio")
    else:
        return redirect("inicio")
    
    
# Vista para editar perfil
def editar_usuario(request, id_usuario):
    verificar = request.session.get("auth", False)
    if verificar:
        if verificar["rol"] == 1 :
            if request.method == "POST":
                try:
                    u = Usuario.objects.get(pk=id_usuario)
                    u.cedula = request.POST.get("cedula")
                    if not u.cedula.isdigit():
                        messages.error(request, "La cédula solo debe contener números.")
                        return redirect("editar_usuario", id_usuario=id_usuario)
                    
                    u.nombre = request.POST.get("nombre")
                    if not re.match(r'^[a-zA-ZáéíóúÁÉÍÓÚñÑ ]+$', u.nombre):
                        messages.error(request, "El nombre solo puede contener letras y espacios.")
                        return redirect("editar_usuario", id_usuario=id_usuario)
                    
                    u.apellido = request.POST.get("apellido")
                    if not re.match(r'^[a-zA-ZáéíóúÁÉÍÓÚñÑ ]+$', u.apellido):
                        messages.error(request, "El apellido solo puede contener letras y espacios.")
                        return redirect("editar_usuario", id_usuario=id_usuario)
                    
                    u.telefono = request.POST.get("telefono")
                    if not validar_telefono(u.telefono):
                        messages.error(request, "El teléfono debe contener entre 7 y 15 dígitos numéricos.")
                        return redirect("editar_usuario", id_usuario=id_usuario)
                    
                    u.direccion = request.POST.get("direccion")
                    if not re.match(r'^[a-zA-Z0-9áéíóúÁÉÍÓÚñÑ ,.]+$', u.direccion):
                        messages.error(request, "La dirección contiene caracteres no permitidos.")
                        return redirect("editar_usuario", id_usuario=id_usuario)
            
                    u.correo = request.POST.get("correo")
                    if not validate_email(u.correo):
                        messages.error(request, "El correo electrónico no tiene un formato válido.")
                        
                    if Usuario.objects.exclude(pk=id_usuario).filter(correo=u.correo).exists():
                        messages.error(request, "Este correo ya está en uso por otro usuario.")
                        return redirect("editar_perfil", id_usuario=id_usuario)
                    
                    u.genero = request.POST.get("genero")
                    u.rol = request.POST.get("rol")
                    u.save()
                    
                    messages.success(request, "Usuario actualizado correctamente!")
                    return redirect("listar_usuarios")
                except Exception as e:  
                    messages.error(request, f"Error: {e}")
                    return redirect("editar_usuario", id_usuario=id_usuario)
            else:
                u = Usuario.objects.get(pk=id_usuario)
                contexto = {"data": u}
                return render(request, 'register.html', contexto)
        else:
            messages.info(request, "Usted no tiene permisos para éste módulo...")
            return redirect("inicio")
    else:
        return redirect("inicio")
    
    
# Eliminar usuario
def eliminar_usuario(request, id_usuario):

# Obtener la instancia
        try:
            usuario_a_eliminar = Usuario.objects.get(pk=id_usuario)

            # Verificar si el usuario tiene sesiones activas
            sesiones_activas = Session.objects.filter(session_data__contains=f'"_auth_user_id":{usuario_a_eliminar.id}')

            if sesiones_activas.exists():
                messages.error(request, "No puedes eliminar a un usuario que tiene la sesión iniciada.")
            else:
                # Eliminar las sesiones del usuario antes de eliminarlo
                sesiones_activas.delete()

                # Eliminar al usuario
                usuario_a_eliminar.delete()
                messages.success(request, "Usuario eliminado correctamente!")

        except Usuario.DoesNotExist:
            messages.error(request, "El usuario no existe.")
        except IntegrityError:
            messages.warning(request, "Error: No puede eliminar el usuario, está en uso.")
        except Exception as e:
            messages.error(request, f"Error: {e}")

        return redirect("listar_usuarios")

# final del CRUD para Usuarios ///////////////////////////////////////////////////////////////////////////////////////////////////

def ventas(request):
    verificar = request.session.get("auth", False)
    if verificar:
        if verificar["rol"] != 3 :
            v = Factura.objects.all()
            contexto = {
                "data": v
                }
            return render(request, "ventas/ventas.html", contexto)
        else:
            messages.info(request, "Usted no tiene permisos para éste módulo...")
        return redirect("inicio")
    else:
        return redirect("inicio")
    
def detalles_venta(request, id_venta):
    detalles = DetalleCompras.objects.filter(factura__id=id_venta)

    total = sum(d.subtotal for d in detalles)  # sumamos todos los subtotales

    return render(request, "ventas/detalles_venta.html", {
        "venta": detalles,
        "total": total
    })
# Vista de productos

def productos(request):
    
    p = Producto.objects.all()
    color = request.GET.get('color')
    tipo = request.GET.get('tipo')
    precio_orden = request.GET.get('precio_orden')
     # Aplicar filtros
    if color:
        p = p.filter(color=color)

    if tipo:
        p = p.filter(tipo=tipo)

    if precio_orden == 'menor':
        p = p.order_by('precio')  # Menor precio primero
    elif precio_orden == 'mayor':
        p = p.order_by('-precio')
    contexto = {
        "data": p,
    }
    return render(request, "productos.html", contexto)

#CRUD para Productos /////////////////////////////////////////////////////////////////////////////////////////////////////////////

# Listar productos
def listar_productos(request):
    verificar = request.session.get("auth", False)
    if verificar:
        if verificar["rol"] != 3:
            p = Producto.objects.all()
            color = request.GET.get('color')
            tipo = request.GET.get('tipo')
            precio_orden = request.GET.get('precio_orden')

            # Aplicar filtros
            if color:
                p = p.filter(color=color)

            if tipo:
                p = p.filter(tipo=tipo)

            if precio_orden == 'menor':
                p = p.order_by('precio')  # Menor precio primero
            elif precio_orden == 'mayor':
                p = p.order_by('-precio')
            contexto = {
                "data": p,
            }
            return render(request, "productos/listar_productos.html", contexto)
        else:
            messages.info(request, "Usted no tiene permisos para éste módulo...")
        return redirect("inicio")
    else:
        return redirect("inicio")


# Verificacion de tipo de imagen

def validate_image_file(value):
    file_type = imghdr.what(value)
    if file_type not in ['png', 'jpeg']:
        raise ValidationError('Solo se permiten archivos .png y .jpg')
    
    # Agregar producto
def agregar_producto(request):
    verificar = request.session.get("auth", False)
    if verificar:
        if verificar["rol"] !=3 :
            if request.method == "POST":
                
                try:
                    request.session["datos"] = request.POST
        
                    nombre = request.POST.get("nombre")
                    if not re.match(r'^[a-zA-Z0-9 ]+$', nombre):
                        messages.error(request, "El nombre solo debe contener letras y números.")
                        return redirect("agregar_producto")
                    
                    medida = request.POST.get("medida")
                    if not re.match(r'^[a-zA-Z0-9 ]+$', medida):
                        messages.error(request, "La medida solo debe contener letras y números.")
                        return redirect("agregar_producto")
                    
                    color = request.POST.get("color")
                    color = color.upper()
                    if not re.match(r'^[a-zA-Z ]+$', color):
                        messages.error(request, "El color solo debe contener letras y espacios.")
                        return redirect("agregar_producto")

                    precio = request.POST.get("precio")
                    if not validar_precio(precio):
                        messages.error(request, "El precio debe ser un número válido con hasta tres decimales.")
                        return redirect("agregar_producto")
                    precio = float(precio)
                    
                    descripcion = request.POST.get("descripcion")
                    
                    cantidad = request.POST.get("cantidad")
                    if not cantidad.isdigit() or int(cantidad) < 0:
                        messages.error(request, "La cantidad debe ser un número positivo.")
                        return redirect("agregar_producto")
                    cantidad = int(cantidad)
                    
                    peso = request.POST.get("peso")
                    if not re.match(r'^[a-zA-Z0-9 ]+$', peso):
                        messages.error(request, "El peso solo debe contener letras y números.")
                        return redirect("agregar_producto")
                    
                    foto = request.FILES.get("foto")
                    if foto:
                        try:
                            validate_image_file(foto)
                        except ValidationError as e:
                            messages.error(request, str(e))
                            return redirect("agregar_producto")
                    else:
                        messages.error(request, "Debes subir una foto del producto.")
                        return redirect("agregar_producto")

                    tipo = request.POST.get("tipo")
                    gen = int(request.POST.get("gen"))
                    
                    p = Producto(
                        nombre=nombre,
                        medida=medida,
                        color=color,
                        precio=precio,
                        descripcion=descripcion,
                        cantidad=cantidad,
                        peso=peso,
                        foto=foto,
                        tipo=tipo,
                        gen=gen
                    )
                    p.save()
                    request.session["datos"] = None
                    messages.success(request, "Producto agregado correctamente!")
                    return redirect("listar_productos")
                except Exception as e:
                    messages.error(request, f"Error: {e}")
                    return redirect("agregar_producto")
            else:
                return render(request, 'productos/formulario_productos.html')
        else:
            messages.info(request, "Usted no tiene permisos para éste módulo...")
            return redirect("inicio")
    else:
        return redirect("inicio")

def validar_precio(valor):
    return re.match(r'^\d+(\.\d{2,3})?$', valor) is not None

#Editar Producto    
def editar_producto(request, producto_id):
    verificar = request.session.get("auth", False)
    if verificar:
        if verificar["rol"] !=3 :
            if request.method == "POST":
                try:
                    p = Producto.objects.get(pk=producto_id)
                    p.nombre = request.POST.get("nombre")
                    
                    if not re.match(r'^[a-zA-Z0-9 ]+$', p.nombre):
                        messages.error(request, "El nombre solo debe contener letras y números.")
                        return redirect("editar_producto", producto_id=producto_id)
                    
                    p.medida = request.POST.get("medida")
                    if not re.match(r'^[a-zA-Z0-9 ]+$', p.medida):
                        messages.error(request, "La medida solo debe contener letras y números.")
                        return redirect("editar_producto", producto_id=producto_id)

                    
                    p.color = request.POST.get("color")
                    if not re.match(r'^[a-zA-Z ]+$', p.color):
                        messages.error(request, "El color solo debe contener letras y espacios.")
                        return redirect("editar_producto", producto_id=producto_id)
                    
                    precio = request.POST.get("precio")
                    if not validar_precio(precio):
                        messages.error(request, "El precio debe ser un número válido con hasta tres decimales.")
                        return redirect("editar_producto", producto_id=producto_id)
                    p.precio = float(precio)
                    
                    p.descripcion = request.POST.get("descripcion")
                    
                    cantidad = request.POST.get("cantidad")
                    if not cantidad.isdigit() or int(cantidad) < 0:
                        messages.error(request, "La cantidad debe ser un número positivo y sin caracteres especiales.")
                        return redirect("editar_producto", producto_id=producto_id)
                    p.cantidad = int(cantidad)
                    
                    peso = request.POST.get("peso")
                    if not re.match(r'^[a-zA-Z0-9 ]+$', peso):
                        messages.error(request, "El peso solo debe contener letras y números.")
                        return redirect("editar_producto", producto_id=producto_id)
                    p.peso = peso
                    
                    p.foto = request.FILES.get("foto", p.foto)
                    if p.foto:
                        try:
                            validate_image_file(p.foto)
                        except ValidationError as e:
                            messages.error(request, str(e))
                            return redirect("editar_producto", producto_id=producto_id)
                    else:
                        messages.error(request, "Debes subir una foto del producto.")
                        return redirect("editar_producto")

                    tipo = request.POST.get("tipo")
                    gen = int(request.POST.get("gen"))
                    
                    p.tipo = request.POST.get("tipo")
                    p.gen = request.POST.get("gen")
                    p.save()
                    
                    messages.success(request, "Producto actualizado correctamente!")
                    return redirect("listar_productos")
                except Exception as e:
                    messages.error(request, f"Error: {e}")
                    return redirect("editar_producto", producto_id=producto_id)
            else:
                p = Producto.objects.get(pk=producto_id)
                contexto = {"data": p}
                return render(request, 'productos/formulario_productos.html', contexto)
        else:
            messages.info(request, "Usted no tiene permisos para éste módulo...")
            return redirect("inicio")
    else:
        return redirect("inicio")
        

#Eliminar Producto
def eliminar_producto(request, producto_id):
    # Obtener la instancia
    try:
        p = Producto.objects.get(pk = producto_id)
        p.delete()
        messages.success(request, "¡Producto eliminado correctamente!")
    except IntegrityError:
        messages.warning(request, "Error: No puede eliminar el producto, está en uso.")
    except Exception as e:
        messages.error(request, f"Error: {e}")

    return redirect("listar_productos")

#Final del CRUD para Productos //////////////////////////////////////////////////////////////////////////////////////////////////      


def correo1(request):
    try:
        html_message = '''Hola mundo <strong style="color: blue;">Django </strong> desde mi app...' \
        <br>
        Bienvenido
        '''
        send_mail(
            "Spa SENA - Pruebas",
            "Mensaje de prueba...... desde Django",
            settings.EMAIL_HOST_USER,
            ["camiloarinconc@gmail.com"],
            fail_silently=False,
            html_message=html_message
            
        )
        return HttpResponse(F"Correo enviado!!")

    except Exception as e:
        return HttpResponse(f"Error: {e}")
    

#favoritos //////////////////////////////////////////////////////////////////////////////////////////////////
def agregar_a_favoritos(request, producto_id):
    verificar = request.session.get("auth", False)
    if verificar:
        """Agrega un producto a la lista de favoritos del usuario."""
        producto = Producto.objects.get(id=producto_id)
        favoritos = request.session.get('favoritos', [])

        if producto_id not in favoritos:
            favoritos.append(producto_id)
            request.session['favoritos'] = favoritos
            return JsonResponse({'status': 'added'})
        else:
            return JsonResponse({'status': 'exists'})
    else:
        return redirect("favoritos.html")

def eliminar_de_favoritos(request, producto_id):
    try:
        p = Producto.objects.get(pk = producto_id)
        p.delete()
        messages.success(request, "producto eliminado correctamente!")
    except IntegrityError:
        messages.warning(request, "Error: No puede eliminar el producto, está en uso.")
    except Exception as e:
        messages.error(request, f"Error: {e}")

    return redirect("favoritos.html")

    """Muestra los productos favoritos guardados en la sesión."""
def favoritos(request):
    verificar = request.session.get("auth", False)
    if verificar:
        if verificar["rol"] == 3:
            favoritos_ids = request.session.get('favoritos', [])
            productos_favoritos = Producto.objects.filter(id__in=favoritos_ids)
            
            return render(request, 'favoritos.html', {'productos': productos_favoritos}) 
        else:
            messages.info(request, "Usted no tiene permisos para éste módulo...")
            return redirect("inicio")
    else:
        return redirect("inicio")
    
def checkout(request):
    carrito = request.session.get('carrito', {})
    carrito_items = []
    total = 0

    for clave_producto, item in carrito.items():
        nombre = item.get('nombre', 'Producto sin nombre')
        precio = item.get('precio', 0)
        foto = item.get('foto', '')
        cantidad = item.get('cantidad', 1)
        talla = item.get('talla', 'N/A')

        subtotal = precio * cantidad
        total += subtotal

        carrito_items.append({
            'id': clave_producto.split('-')[0], 
            'nombre': nombre,
            'precio': precio,
            'foto': foto,
            'cantidad': cantidad,
            'talla': talla,
            'subtotal': subtotal
        })

    return render(request, 'checkout.html', {'carrito_items': carrito_items, 'total': total})

@transaction.atomic
def procesar_pago(request):
    if not request.session.get("auth"):
        return redirect("login")

    if request.method == "POST":
        usuario_id = request.session["auth"]["id"]
        usuario = Usuario.objects.get(id=usuario_id)
        medio_pago = request.POST.get("medio_pago")

        carrito = request.session.get("carrito", {})

        if not carrito:
            return redirect("checkout")

        total = sum(item["precio"] * item["cantidad"] for item in carrito.values())

        factura = Factura.objects.create(
            cliente=usuario,
            precio=total,
            total=total,
            fecha=now(),
            medioPago=int(medio_pago)
        )

        productos_serializados = []

        for clave, item in carrito.items():
            producto_id = clave.split("-")[0]
            producto = Producto.objects.get(id=producto_id)
            cantidad = item["cantidad"]
            subtotal = item["precio"] * cantidad
            talla = item.get("talla", "N/A")

            DetalleCompras.objects.create(
                factura=factura,
                precioProducto=producto,
                cantidad=cantidad,
                subtotal=subtotal,
                talla=talla
            )

            producto.cantidad -= cantidad
            if producto.cantidad < 0:
                producto.cantidad = 0
            producto.save()

            productos_serializados.append({
                "nombre": producto.nombre,
                "precio": producto.precio,
                "cantidad": cantidad,
                "talla": talla,
                "subtotal": subtotal
            })

        request.session["confirmacion_pago"] = {
            "nombre": usuario.nombre,
            "direccion": usuario.direccion,
            "email": usuario.correo,
            "medio_pago": dict(Factura.MEDIOPAGO).get(int(medio_pago), "Desconocido"),
            "total": total,
            "productos": productos_serializados
        }

        request.session["carrito_factura"] = carrito

        request.session["carrito"] = {}

        messages.success(request, "Pago procesado con éxito. Gracias por tu compra.")
        return redirect("confirmacion_pago")

    return redirect("checkout")

def confirmacion_pago(request):
    datos_pago = request.session.get("confirmacion_pago", {})

    if not datos_pago:
        return redirect("checkout")  

    return render(request, "confirmacion_pago.html", {"datos_pago": datos_pago})



def descargar_factura_pdf(request):
    datos_pago = request.session.get("confirmacion_pago", {})
    carrito = request.session.get("carrito_factura", [])
    numero_factura = f"FAC-{uuid.uuid4().hex[:6].upper()}"
    
    fecha_actual = datetime.date.today().strftime("%d/%m/%Y")

    if not datos_pago or not carrito:
        return redirect("checkout")
    
    logo_path = os.path.join(settings.BASE_DIR, 'sevenoneseven', 'static', 'img', '717logo.png')
    buffer = BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    if os.path.exists(logo_path):
        print(logo_path)
        logo = ImageReader(logo_path)
        pdf.drawImage(logo, width - 4.5*cm, height - 3*cm, width=3*cm, preserveAspectRatio=True)
    else:
        print("ruta no encontrada")

    pdf.setFont("Helvetica-Bold", 28)
    pdf.drawString(2*cm, height - 2*cm, "Factura - 717")

    pdf.setFont("Helvetica", 10)
    pdf.drawString(2*cm, height - 3.5*cm, "DE")
    pdf.drawString(2*cm, height - 4.1*cm, "Tienda 717")
    pdf.drawString(2*cm, height - 4.6*cm, "Calle Principal 123")
    pdf.drawString(2*cm, height - 5.1*cm, "Medellin, Colombia")

    pdf.drawString(10*cm, height - 3.5*cm, "N° DE FACTURA")
    pdf.drawString(15.5*cm, height - 3.5*cm, numero_factura)
    pdf.drawString(10*cm, height - 4.1*cm, "FECHA")
    pdf.drawString(15.5*cm, height - 4.1*cm, fecha_actual)
    pdf.drawString(10*cm, height - 4.6*cm, "N° DE PEDIDO")
    pdf.drawString(15.5*cm, height - 4.6*cm, "0001")
    pdf.drawString(10*cm, height - 5.1*cm, "FECHA VENCIMIENTO")
    pdf.drawString(15.5*cm, height - 5.1*cm, fecha_actual)

    pdf.setFont("Helvetica-Bold", 10)
    pdf.drawString(2*cm, height - 6.5*cm, "FACTURAR A")
    pdf.drawString(10*cm, height - 6.5*cm, "ENVIAR A")

    pdf.setFont("Helvetica", 10)
    pdf.drawString(2*cm, height - 7.1*cm, datos_pago["nombre"])
    pdf.drawString(2*cm, height - 7.6*cm, datos_pago["direccion"])

    pdf.drawString(10*cm, height - 7.1*cm, datos_pago["nombre"])
    pdf.drawString(10*cm, height - 7.6*cm, datos_pago["direccion"])

    pdf.setFont("Helvetica-Bold", 10)
    pdf.drawString(2*cm, height - 9*cm, "CANT.")
    pdf.drawString(3.5*cm, height - 9*cm, "DESCRIPCIÓN")
    pdf.drawString(13*cm, height - 9*cm, "PRECIO UNITARIO")
    pdf.drawString(17*cm, height - 9*cm, "IMPORTE")

    pdf.line(2*cm, height - 9.2*cm, 19*cm, height - 9.2*cm)

    y = height - 9.8*cm
    total = 0
    pdf.setFont("Helvetica", 10)

    for _, item in carrito.items():
        cantidad = item["cantidad"]
        nombre = item["nombre"]
        precio = float(item["precio"])
        subtotal = cantidad * precio
        total += subtotal

        pdf.drawString(2*cm, y, str(cantidad))
        pdf.drawString(3.5*cm, y, nombre[:40]) 
        pdf.drawRightString(16.5*cm, y, f"{precio:.2f}")
        pdf.drawRightString(19*cm, y, f"{subtotal:.2f}")
        y -= 0.6*cm

    pdf.setFont("Helvetica", 10)
    pdf.drawRightString(18*cm, y - 0.3*cm, f"Subtotal: {total:.2f}")

    pdf.setFont("Helvetica-Bold", 14)
    pdf.drawString(2*cm, y - 2*cm, "TOTAL")
    pdf.rect(1.8*cm, y - 2.3*cm, 16.5*cm, 1.2*cm)
    pdf.drawRightString(18*cm, y - 1.7*cm, f"{total:.2f}$")

    pdf.setFont("Helvetica-Bold", 10)
    pdf.drawString(2*cm, y - 4*cm, "CONDICIONES Y FORMA DE PAGO")

    pdf.setFont("Helvetica", 10)
    pdf.drawString(2*cm, y - 4.7*cm, "Banco Santander")
    pdf.drawString(2*cm, y - 5.2*cm, "IBAN: ES12 3456 7891")
    pdf.drawString(2*cm, y - 5.7*cm, "SWIFT/BIC: ABCDESM1XXX")

    pdf.showPage()
    pdf.save()
    buffer.seek(0)

    del request.session["carrito_factura"]
    return HttpResponse(buffer, content_type='application/pdf', headers={
        'Content-Disposition': 'attachment; filename="Factura_717.pdf"'
    })


def enviar_factura_por_correo(request):
    datos_pago = request.session.get("confirmacion_pago", {})

    if not datos_pago:
        return redirect("checkout")

    buffer = BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=letter)
    width, height = letter

    pdf.setFont("Helvetica-Bold", 20)
    pdf.drawString(50, height - 80, "Factura Electrónica - 717")

    logo_path = os.path.join('static', 'img', '717logo.png')
    if os.path.exists(logo_path):
        logo = ImageReader(logo_path)
        pdf.drawImage(logo, width - 130, height - 110, width=80, preserveAspectRatio=True, mask='auto')

    pdf.setFont("Helvetica", 12)
    pdf.drawString(50, height - 120, f"Fecha: {datetime.now().strftime('%d/%m/%Y')}")
    pdf.drawString(50, height - 140, f"Número de Factura: FAC-{datos_pago.get('id', 'XXXXXX')}")

    pdf.drawString(50, height - 180, f"Nombre: {datos_pago['nombre']}")
    pdf.drawString(50, height - 200, f"Correo: {datos_pago['email']}")
    pdf.drawString(50, height - 220, f"Dirección: {datos_pago['direccion']}")
    pdf.drawString(50, height - 240, f"Método de Pago: {datos_pago['medio_pago']}")

    pdf.line(50, height - 260, width - 50, height - 260)

    y = height - 280
    pdf.setFont("Helvetica-Bold", 12)
    pdf.drawString(50, y, "Cant.")
    pdf.drawString(100, y, "Descripción")
    pdf.drawString(350, y, "Precio Unit.")
    pdf.drawString(450, y, "Total")

    y -= 20
    pdf.setFont("Helvetica", 12)

    productos = datos_pago.get("productos", []) 
    for producto in productos:
        pdf.drawString(50, y, str(producto['cantidad']))
        pdf.drawString(100, y, producto['nombre'])
        pdf.drawString(350, y, f"${producto['precio']}")
        pdf.drawString(450, y, f"${producto['precio'] * producto['cantidad']}")
        y -= 20
        if y < 100: 
            pdf.showPage()
            y = height - 80

    y -= 20
    pdf.setFont("Helvetica-Bold", 14)
    pdf.drawString(350, y, "TOTAL:")
    pdf.drawString(450, y, f"${datos_pago['total']}")

    pdf.showPage()
    pdf.save()
    buffer.seek(0)

    email = EmailMessage(
        subject='Factura de tu compra en 717 Tienda',
        body='Adjunto encontrarás la factura de tu compra. ¡Gracias por confiar en nosotros!',
        from_email='717days@gmail.com',
        to=[datos_pago['email']],
    )
    email.attach('Factura_717.pdf', buffer.read(), 'application/pdf')
    email.send()

    messages.success(request, "Factura enviada al correo correctamente.")
    return redirect("confirmacion_pago")


