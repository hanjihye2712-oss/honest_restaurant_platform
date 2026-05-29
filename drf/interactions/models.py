from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator, MaxValueValidator


class Bookmark(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="bookmarks",
    )
    restaurant = models.ForeignKey(
        "honest_restaurant.PublicRestaurantData",
        on_delete=models.CASCADE,
        related_name="bookmarks",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "bookmark"
        unique_together = [("user", "restaurant")]
        ordering = ["-created_at"]
        verbose_name = "북마크"
        verbose_name_plural = "북마크"

    def __str__(self):
        return f"{self.user.username} → {self.restaurant.name}"


class Rating(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="ratings",
    )
    restaurant = models.ForeignKey(
        "honest_restaurant.PublicRestaurantData",
        on_delete=models.CASCADE,
        related_name="ratings",
    )
    score = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        verbose_name="별점",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "rating"
        unique_together = [("user", "restaurant")]
        ordering = ["-updated_at"]
        verbose_name = "별점"
        verbose_name_plural = "별점"

    def __str__(self):
        return f"{self.user.username} → {self.restaurant.name} ({self.score}점)"


class Review(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="interaction_reviews",
    )
    restaurant = models.ForeignKey(
        "honest_restaurant.PublicRestaurantData",
        on_delete=models.CASCADE,
        related_name="interaction_reviews",
    )
    content = models.TextField(verbose_name="리뷰 내용")
    image   = models.ImageField(upload_to="review_images/", blank=True, null=True, verbose_name="리뷰 이미지 1")
    image_2 = models.ImageField(upload_to="review_images/", blank=True, null=True, verbose_name="리뷰 이미지 2")
    image_3 = models.ImageField(upload_to="review_images/", blank=True, null=True, verbose_name="리뷰 이미지 3")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "review"
        unique_together = [("user", "restaurant")]
        ordering = ["-created_at"]
        verbose_name = "리뷰"
        verbose_name_plural = "리뷰"

    def __str__(self):
        return f"{self.user.username} → {self.restaurant.name}"
