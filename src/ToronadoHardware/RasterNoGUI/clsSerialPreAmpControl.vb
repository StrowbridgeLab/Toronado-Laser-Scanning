Imports System
Imports System.IO.Ports
Public Class clsSerialPreAmpControl
    ' last revised 29 Dec 2017 BWS
    Dim WithEvents PreAmpSerial As SerialPort
    Dim retText As String = ""
    Dim MyComPortStr As String = ""
    Dim MyPMTnameStr As String = ""
    Dim ComPortStarted As Boolean = False
    Dim CurrentPreAmpSettingsStr As String = ""

    Friend Function StartPort(ByVal ComStr As String, PMTname As String) As Boolean
        ' used to start COMM port; if friend functions can still be called if COMM never started (but will be ignored)
        PreAmpSerial = New SerialPort(ComStr, 9600, Parity.None, 8, 2) ' For SRS570 preamp
        MyComPortStr = ComStr
        Try
            AddHandler PreAmpSerial.DataReceived, AddressOf GotDataIn
            PreAmpSerial.Open()
            ComPortStarted = True
            Return True
        Catch ex As Exception
            MsgBox("Problem opening serial connection to SRS570 PreAmp on " + MyComPortStr + ": " + ex.Message)
            Return False
        End Try
    End Function

    Friend Function getSetttings() As String
        ' Used to return a string that contains the last settings sent to this particular SRS570 preamp
        Return CurrentPreAmpSettingsStr
    End Function

    Friend Function SetInvert(newValue As Long) As Boolean
        '  SendPreAmpText("INVT " + CStr(newValue))
        Return True
    End Function
    Friend Function SetRasterDefault() As Boolean
        If ComPortStarted Then
            Dim DescStr As String = ""
            DescStr += "(Default) "
            SendPreAmpText("SENS 18", DescStr) ' 1 uA/V sensitivity
            SendPreAmpText("FLTT 5", DescStr) ' bypass filter
            SendPreAmpText("GNMD 1", DescStr) ' high bandwidth mode
            SendPreAmpText("INVT 1", DescStr) ' Invert mode
            SendPreAmpText("SUCM 0", DescStr) ' Use calibrated sensitivity
            SendPreAmpText("IOON 0", DescStr) ' Turn off input offset current
            SendPreAmpText("BSON 0", DescStr) ' Turn off bias voltage
            Return True
        Else
            Return False
        End If
    End Function
    Friend Function SetPhotometryMode(newValue As Long) As Boolean
        ' Enables automatic switching between high bandwidth mode for raster scanning (newValue=0) and high sensitivity mode(newValue=1)
        If ComPortStarted Then
            Dim DescStr As String = "PMT " + MyPMTnameStr + " on " + MyComPortStr + ": "
            If newValue = 1 Then
                ' photometry mode with high sensitivity and low bandwidth
                DescStr += "(Photometry) "
                SendPreAmpText("SENS 15", DescStr) ' 50 nA/V sensitivity
                SendPreAmpText("LFRQ 10", DescStr) ' 3 kHz low-pass filter
              
                SendPreAmpText("FLTT 3", DescStr) ' engage low-pass filter
                SendPreAmpText("GNMD 0", DescStr) ' low noise mode
            Else
                ' regular raster scanning mode
                DescStr += "(Raster) "
                SendPreAmpText("SENS 18", DescStr) ' 1 uA/V sensitivity
                SendPreAmpText("FLTT 5", DescStr) ' bypass filter
                SendPreAmpText("GNMD 1", DescStr) ' high bandwidth mode
            End If
            Return True
        Else
            ' Port not started
            Return False
        End If
    End Function

    ' local functions below here

    Private Function SendPreAmpText(ByVal newText As String, ByRef descStr As String) As Boolean
        If ComPortStarted Then
            Try
                PreAmpSerial.WriteLine(newText + vbCrLf)
                descStr += newText + " | "
                Return True
            Catch ex As Exception
                MsgBox("SRS570 serial exception on " + MyComPortStr + ": " + ex.Message)
                Return False
            End Try
        Else
            ' port not started so ignore text and return False
            Return False
        End If
    End Function
    Private Sub GotDataIn(ByVal sender As Object, ByVal e As SerialDataReceivedEventArgs)
        Dim TempStr As String = ""
        For i As Long = 0 To 10
            For j As Long = 0 To 232
                Application.DoEvents()
            Next
        Next
        Do
            TempStr = TempStr + PreAmpSerial.ReadExisting
            Application.DoEvents()
        Loop Until PreAmpSerial.BytesToRead = 0
        retText = TempStr ' ignored for SRS570 since write-only serial connection
        '  MsgBox("Got text from PreAmp: " + retText)
    End Sub

End Class
