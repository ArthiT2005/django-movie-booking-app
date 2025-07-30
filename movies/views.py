from django.shortcuts import render, redirect, get_object_or_404
from .models import Movie, Theater, Seat, Booking
from django.contrib.auth.decorators import login_required
from django.db import IntegrityError
from django.utils.timezone import now, localdate
from datetime import timedelta


def movie_list(request):
    search_query = request.GET.get('search')
    if search_query:
        movies = Movie.objects.filter(name__icontains=search_query)
    else:
        movies = Movie.objects.all()

    today = localdate()
    today_theaters = Theater.objects.filter(time__date=today)

    return render(request, 'movies/movie_list.html', {
        'movies': movies,
        'today_theaters': today_theaters,  # ✅ Highlight today's shows
        'today': today
    })


def movie_detail(request, movie_id):
    movie = get_object_or_404(Movie, id=movie_id)
    theaters = Theater.objects.filter(movie=movie)
    trailer_embed = None

    # ✅ Auto-convert YouTube URL to embeddable format
    if movie.trailer_url and 'watch?v=' in movie.trailer_url:
        trailer_embed = movie.trailer_url.replace('watch?v=', 'embed/')

    return render(request, 'movies/movie_detail.html', {
        'movie': movie,
        'theaters': theaters,
        'trailer_embed': trailer_embed  # ✅ Trailer support
    })


def theater_list(request, movie_id):
    movie = get_object_or_404(Movie, id=movie_id)
    theaters = Theater.objects.filter(movie=movie)
    return render(request, 'movies/theater_list.html', {
        'movie': movie,
        'theaters': theaters
    })


@login_required(login_url='/login/')
def book_seats(request, theater_id):
    theater = get_object_or_404(Theater, id=theater_id)
    seats = Seat.objects.filter(theater=theater)

    # ✅ Clear expired reservations before showing
    for seat in seats:
        seat.release_reservation_if_expired()

    if request.method == 'POST':
        selected_seats = request.POST.getlist('seats')
        error_seats = []

        if not selected_seats:
            return render(request, "movies/seat_selection.html", {
                'theater': theater,
                "seats": seats,
                'error': "No seat selected.",
                'countdown_minutes': 5
            })

        for seat_id in selected_seats:
            seat = get_object_or_404(Seat, id=seat_id, theater=theater)

            # Skip if already reserved/booked
            if seat.is_reserved() or seat.is_booked:
                error_seats.append(seat.seat_number)
                continue

            try:
                seat.reserved_by = request.user
                seat.reserved_until = now() + timedelta(minutes=5)  # ✅ 5-minute reservation timeout
                seat.is_booked = False
                seat.save()

                Booking.objects.create(
                    user=request.user,
                    seat=seat,
                    movie=theater.movie,
                    theater=theater
                )

            except IntegrityError:
                error_seats.append(seat.seat_number)

        if error_seats:
            return render(request, "movies/seat_selection.html", {
                'theater': theater,
                "seats": seats,
                'error': f"Seats already booked or reserved: {', '.join(error_seats)}",
                'countdown_minutes': 5
            })

        return redirect('profile')  # redirect after booking

    return render(request, "movies/seat_selection.html", {
        'theater': theater,
        "seats": seats,
        'countdown_minutes': 5  # ⏳ add countdown support
    })
