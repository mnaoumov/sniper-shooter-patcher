.class public abstract Lcom/google/b/a/a/a;
.super Landroid/support/v4/app/i;
.source "BaseGameActivity.java"

# interfaces
.implements Lcom/google/b/a/a/c;


# instance fields
.field protected o:Lcom/google/b/a/a/b;

.field protected p:I


# direct methods
.method protected constructor <init>()V
    .locals 1

    .prologue
    invoke-direct {p0}, Landroid/support/v4/app/i;-><init>()V

    const/4 v0, 0x1

    iput v0, p0, Lcom/google/b/a/a/a;->p:I

    new-instance v0, Lcom/google/b/a/a/b;

    invoke-direct {v0, p0}, Lcom/google/b/a/a/b;-><init>(Landroid/app/Activity;)V

    iput-object v0, p0, Lcom/google/b/a/a/a;->o:Lcom/google/b/a/a/b;

    return-void
.end method

.method protected constructor <init>(I)V
    .locals 1

    .prologue
    invoke-direct {p0}, Landroid/support/v4/app/i;-><init>()V

    const/4 v0, 0x1

    iput v0, p0, Lcom/google/b/a/a/a;->p:I

    iput p1, p0, Lcom/google/b/a/a/a;->p:I

    return-void
.end method


# virtual methods
.method protected A()Lcom/google/android/gms/common/a;
    .locals 1

    .prologue
    const/4 v0, 0x0

    return-object v0
.end method

.method protected b(I)V
    .locals 0

    .prologue
    iput p1, p0, Lcom/google/b/a/a/a;->p:I

    return-void
.end method

.method protected b(Ljava/lang/String;Ljava/lang/String;)V
    .locals 0

    .prologue
    return-void
.end method

.method protected onActivityResult(IILandroid/content/Intent;)V
    .locals 0

    .prologue
    invoke-super {p0, p1, p2, p3}, Landroid/support/v4/app/i;->onActivityResult(IILandroid/content/Intent;)V

    return-void
.end method

.method protected onCreate(Landroid/os/Bundle;)V
    .locals 0

    .prologue
    invoke-super {p0, p1}, Landroid/support/v4/app/i;->onCreate(Landroid/os/Bundle;)V

    return-void
.end method

.method protected onStart()V
    .locals 0

    .prologue
    invoke-super {p0}, Landroid/support/v4/app/i;->onStart()V

    return-void
.end method

.method protected onStop()V
    .locals 0

    .prologue
    invoke-super {p0}, Landroid/support/v4/app/i;->onStop()V

    return-void
.end method

.method protected w()Z
    .locals 1

    .prologue
    const/4 v0, 0x0

    return v0
.end method

.method protected x()V
    .locals 0

    .prologue
    return-void
.end method

.method protected y()V
    .locals 0

    .prologue
    return-void
.end method

.method protected z()Z
    .locals 1

    .prologue
    const/4 v0, 0x0

    return v0
.end method
