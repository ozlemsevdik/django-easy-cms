import hashlib

from jsonfield import JSONField
from hvad.models import TranslatableModel, TranslatedFields

from django.db import models
from django.db.models.signals import post_save

from django.core.cache import cache
from django.contrib.sites.models import Site


class Placeholder(models.Model):

    name = models.SlugField(max_length=50)
    view_name = models.CharField(max_length=100, db_index=True,
                                 null=True, blank=True)
    widget_config = JSONField(default="[]")
    template_name = models.CharField(max_length=50, null=True, blank=True)

    # Foreign Keys
    site = models.ForeignKey('sites.Site')

    class Meta:
        unique_together = ('name', 'view_name')

    def __unicode__(self):
        return self.name


class Content(TranslatableModel):

    name = models.SlugField(max_length=50, unique=True)
    image = models.ImageField(upload_to='contents', null=True, blank=True)
    parent = models.ForeignKey('easy_cms.Content', null=True, blank=True,
                               related_name='children')
    created_at = models.DateTimeField(auto_now_add=True)
    template_name = models.CharField(max_length=50, null=True, blank=True)

    # Translations
    translations = TranslatedFields(
        title=models.CharField(max_length=255, null=True, blank=True),
        tagline=models.CharField(max_length=255, null=True, blank=True),
        content=models.TextField(null=True, blank=True),
        description=models.CharField(max_length=500, null=True, blank=True),
        url=models.CharField(max_length=255, null=True, blank=True)
    )

    # Foreign Keys
    site = models.ForeignKey('sites.Site')

    def __unicode__(self):
        return self.name

    def save(self, *args, **kwargs):
        if self.parent:
            try:
                self.site
            except Site.DoesNotExist:
                self.site = self.parent.site
        for child in self.children.all():
            if child.site != self.site:
                child.site = self.site
                child.save()
        super(Content, self).save(*args, **kwargs)


def placeholder_post_save(sender, instance, **kwargs):
    site = Site.objects.get_current()
    container = Placeholder.objects.get(name=instance.name, site=site)

    for c in container.widget_config:

        cache_enabled = c.get('cache_enabled')
        cache_key_prefix = c.get('cache_key_prefix')
        template_name = c.get('template_name')
        widget_name = c.get('name')
        cache_key = c.get('cache_key')

        if cache_enabled:
            md5 = hashlib.md5()
            md5.update(cache_key_prefix or '')
            md5.update(cache_key or widget_name)
            md5.update(template_name or '')
            cache_key = md5.hexdigest()

            cache.delete(cache_key)


post_save.connect(placeholder_post_save, sender=Placeholder)
