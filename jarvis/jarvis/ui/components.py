
import flet as ft
import math

class Orb(ft.Container):
    def __init__(self):
        super().__init__()
        self.state = "IDLE"  # IDLE, LISTENING, THINKING, SPEAKING
        self.orb_container = ft.Container(
            width=200,
            height=200,
            border_radius=100,
            gradient=ft.RadialGradient(
                colors=["cyan100", "cyan700", "transparent"],
                stops=[0.1, 0.6, 1.0],
            ),
            animate_scale=ft.Animation(1000, ft.AnimationCurve.EASE_IN_OUT),
            animate_opacity=ft.Animation(500, ft.AnimationCurve.EASE_IN_OUT),
        )
        self.content = self.orb_container
        self.alignment = ft.alignment.Alignment(0, 0)  # center
        self.expand = True

    def set_state(self, state: str):
        self.state = state
        
        if state == "IDLE":
            self.orb_container.scale = 1.0
            self.orb_container.gradient.colors = ["cyan50", "cyan700", "transparent"]
        elif state == "LISTENING":
            self.orb_container.scale = 1.2
            self.orb_container.gradient.colors = ["red50", "red700", "transparent"]
        elif state == "THINKING":
            self.orb_container.scale = 0.8
            self.orb_container.gradient.colors = ["yellow50", "yellow700", "transparent"]
        elif state == "SPEAKING":
            self.orb_container.scale = 1.1
            self.orb_container.gradient.colors = ["blue50", "blue700", "transparent"]
            
        self.orb_container.update()

class StatRing(ft.Column):
    def __init__(self, label: str, value: float, color: str = "cyan"):
        super().__init__()
        self.label = label
        self.value_val = value
        self.color = color
        
        self.progress_ring = ft.ProgressRing(
            value=self.value_val, 
            stroke_width=5, 
            color=self.color, 
            bgcolor=ft.colors.with_opacity(0.2, self.color) if hasattr(ft, 'colors') else "cyan100",
            width=60, height=60
        )
        # Fallback for bgcolor if with_opacity fails due to string
        # Actually with_opacity handles strings in recent flet? No, usually needs color obj or we pick a hex.
        # Let's just use a dimmer color string.
        self.progress_ring.bgcolor = ft.colors.with_opacity(0.1, str(self.color)) if hasattr(ft, 'colors') else "grey"

        self.value_text = ft.Text(f"{int(self.value_val * 100)}%", size=12, weight="bold")
        
        self.controls = [
            ft.Stack(
                [
                    self.progress_ring,
                    ft.Container(content=self.value_text, alignment=ft.alignment.Alignment(0, 0), width=60, height=60)
                ]
            ),
            ft.Text(self.label, size=10, color="grey400")
        ]
        self.horizontal_alignment = ft.CrossAxisAlignment.CENTER

    def update_value(self, new_value: float):
        self.value_val = new_value
        self.progress_ring.value = new_value
        self.value_text.value = f"{int(new_value * 100)}%"
        self.update()

class HexButton(ft.Container):
    def __init__(self, icon_name: str, on_click):
        super().__init__()
        self.icon_name = icon_name
        
        self.content = ft.Icon(self.icon_name, color="cyan200", size=24)
        self.width = 50
        self.height = 50
        self.border = ft.border.all(1, "cyan700")
        self.border_radius = 10
        self.on_click = on_click
        self.alignment = ft.alignment.Alignment(0, 0)  # center
        self.bgcolor = "cyan,0.1" # Flet supports "color,opacity" syntax sometimes or just use distinct color
        # Actually let's just use a dark cyan
        self.bgcolor = "#1A4D4D"
