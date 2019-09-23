<Global.Microsoft.VisualBasic.CompilerServices.DesignerGenerated()> _
Partial Class frmRaster
    Inherits System.Windows.Forms.Form

    'Form overrides dispose to clean up the component list.
    <System.Diagnostics.DebuggerNonUserCode()> _
    Protected Overrides Sub Dispose(ByVal disposing As Boolean)
        Try
            If disposing AndAlso components IsNot Nothing Then
                components.Dispose()
            End If
        Finally
            MyBase.Dispose(disposing)
        End Try
    End Sub

    'Required by the Windows Form Designer
    Private components As System.ComponentModel.IContainer

    'NOTE: The following procedure is required by the Windows Form Designer
    'It can be modified using the Windows Form Designer.  
    'Do not modify it using the code editor.
    <System.Diagnostics.DebuggerStepThrough()> _
    Private Sub InitializeComponent()
        Me.cmdOpenShutter = New System.Windows.Forms.Button()
        Me.cmdCloseShutter = New System.Windows.Forms.Button()
        Me.Label1 = New System.Windows.Forms.Label()
        Me.pnlPhaseJitterOn = New System.Windows.Forms.Label()
        Me.pnlPhaseDither = New System.Windows.Forms.Label()
        Me.SuspendLayout()
        '
        'cmdOpenShutter
        '
        Me.cmdOpenShutter.Location = New System.Drawing.Point(124, 15)
        Me.cmdOpenShutter.Name = "cmdOpenShutter"
        Me.cmdOpenShutter.Size = New System.Drawing.Size(85, 25)
        Me.cmdOpenShutter.TabIndex = 4
        Me.cmdOpenShutter.Text = "Open Shutter"
        Me.cmdOpenShutter.UseVisualStyleBackColor = True
        '
        'cmdCloseShutter
        '
        Me.cmdCloseShutter.Location = New System.Drawing.Point(26, 15)
        Me.cmdCloseShutter.Name = "cmdCloseShutter"
        Me.cmdCloseShutter.Size = New System.Drawing.Size(85, 25)
        Me.cmdCloseShutter.TabIndex = 5
        Me.cmdCloseShutter.Text = "Close Shutter"
        Me.cmdCloseShutter.UseVisualStyleBackColor = True
        '
        'Label1
        '
        Me.Label1.AutoSize = True
        Me.Label1.Location = New System.Drawing.Point(13, 58)
        Me.Label1.Name = "Label1"
        Me.Label1.Size = New System.Drawing.Size(225, 13)
        Me.Label1.TabIndex = 6
        Me.Label1.Text = "DO-0 Shutter, -1 pockels cell, -2 PMT/position"
        '
        'pnlPhaseJitterOn
        '
        Me.pnlPhaseJitterOn.AutoSize = True
        Me.pnlPhaseJitterOn.Font = New System.Drawing.Font("Microsoft Sans Serif", 9.75!, System.Drawing.FontStyle.Bold, System.Drawing.GraphicsUnit.Point, CType(0, Byte))
        Me.pnlPhaseJitterOn.ForeColor = System.Drawing.Color.FromArgb(CType(CType(192, Byte), Integer), CType(CType(0, Byte), Integer), CType(CType(0, Byte), Integer))
        Me.pnlPhaseJitterOn.Location = New System.Drawing.Point(170, 82)
        Me.pnlPhaseJitterOn.Name = "pnlPhaseJitterOn"
        Me.pnlPhaseJitterOn.Size = New System.Drawing.Size(0, 16)
        Me.pnlPhaseJitterOn.TabIndex = 8
        '
        'pnlPhaseDither
        '
        Me.pnlPhaseDither.AutoSize = True
        Me.pnlPhaseDither.Font = New System.Drawing.Font("Microsoft Sans Serif", 9.75!, System.Drawing.FontStyle.Bold, System.Drawing.GraphicsUnit.Point, CType(0, Byte))
        Me.pnlPhaseDither.ForeColor = System.Drawing.Color.FromArgb(CType(CType(192, Byte), Integer), CType(CType(0, Byte), Integer), CType(CType(0, Byte), Integer))
        Me.pnlPhaseDither.Location = New System.Drawing.Point(61, 82)
        Me.pnlPhaseDither.Name = "pnlPhaseDither"
        Me.pnlPhaseDither.Size = New System.Drawing.Size(120, 16)
        Me.pnlPhaseDither.TabIndex = 9
        Me.pnlPhaseDither.Text = "Phase Dither On"
        Me.pnlPhaseDither.Visible = False
        '
        'frmRaster
        '
        Me.AutoScaleDimensions = New System.Drawing.SizeF(6.0!, 13.0!)
        Me.AutoScaleMode = System.Windows.Forms.AutoScaleMode.Font
        Me.ClientSize = New System.Drawing.Size(247, 105)
        Me.Controls.Add(Me.pnlPhaseDither)
        Me.Controls.Add(Me.pnlPhaseJitterOn)
        Me.Controls.Add(Me.Label1)
        Me.Controls.Add(Me.cmdCloseShutter)
        Me.Controls.Add(Me.cmdOpenShutter)
        Me.MaximizeBox = False
        Me.MinimizeBox = False
        Me.Name = "frmRaster"
        Me.Text = "ToronadoHardware"
        Me.ResumeLayout(False)
        Me.PerformLayout()

    End Sub
    Friend WithEvents cmdOpenShutter As System.Windows.Forms.Button
    Friend WithEvents cmdCloseShutter As System.Windows.Forms.Button
    Friend WithEvents Label1 As System.Windows.Forms.Label
    Friend WithEvents pnlPhaseJitterOn As System.Windows.Forms.Label
    Friend WithEvents pnlPhaseDither As System.Windows.Forms.Label

End Class
