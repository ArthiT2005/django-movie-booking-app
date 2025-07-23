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

    # ✅ Highlight current day shows
    today = localdate()
    today_theaters = Theater.objects.filter(time__date=today)

    return render(request, 'movies/movie_list.html', {
        'movies': movies,
        'today_theaters': today_theaters,
        'today': today
    })


def movie_detail(request, movie_id):
    # ✅ Shows movie trailer and all showtimes
    movie = get_object_or_404(Movie, id=movie_id)
    theaters = Theater.objects.filter(movie=movie)
    return render(request, 'movies/movie_detail.html', {
        'movie': movie,
        'theaters': theaters
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

    # ✅ Release expired reservations
    for seat in seats:
        seat.release_reservation_if_expired()

    if request.method == 'POST':
        selected_seats = request.POST.getlist('seats')
        error_seats = []

        if not selected_seats:
            return render(request, "movies/seat_selection.html", {
                'theater': theater,
                "seats": seats,
                'error': "No seat selected."
            })

        for seat_id in selected_seats:
            seat = get_object_or_404(Seat, id=seat_id, theater=theater)

            # Skip if still reserved or booked
            if seat.is_reserved() or seat.is_booked:
                error_seats.append(seat.seat_number)
                continue

            try:
                seat.reserved_by = request.user
                seat.reserved_until = now() + timedelta(minutes=5)
                seat.is_booked = False  # will be True only after payment (optional logic)
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
                'error': f"Seats already booked or reserved: {', '.join(error_seats)}"
            })

        return redirect('profile')  # 🔁 Redirect after booking (e.g., to confirmation page)

    return render(request, "movies/seat_selection.html", {
        'theater': theater,
        "seats": seats
    })
