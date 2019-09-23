Imports System.IO
Imports System.Net.Sockets
Imports System.Threading

Public Class benTCPlistener

    Private mCallingInstance As frmRaster
    Private mTempInputFile As String
    Private mEnable As Boolean = False
    Private serverSocket As System.Net.Sockets.TcpListener
    Private ipLocalEndPoint As System.Net.IPEndPoint
 
    Public Sub New(ByVal callingInstance As frmRaster, ByVal tempInputFile As String, ByVal listenIP As String, ByVal listerPort As Integer)
        mCallingInstance = callingInstance
        mTempInputFile = tempInputFile
        Dim ipAddress As System.Net.IPAddress = System.Net.IPAddress.Parse(listenIP)
        ipLocalEndPoint = New System.Net.IPEndPoint(ipAddress, listerPort)
    End Sub

    Public Sub Start()
        mEnable = True
        Dim listenThread As New Thread(New ThreadStart(AddressOf listenForClients))
        listenThread.Start()
    End Sub

    Private Sub listenForClients()
        serverSocket = New TcpListener(ipLocalEndPoint)
        serverSocket.Start()
        While True
            Dim client As TcpClient = Me.serverSocket.AcceptTcpClient()
            Dim clientThread As New Thread(New ParameterizedThreadStart(AddressOf handleClientComm))
            clientThread.Start(client)
        End While
    End Sub

    Private Sub handleClientComm(ByVal client As Object)
        Dim writeStream As New FileStream(mTempInputFile, FileMode.Create, FileAccess.Write)
        Dim tcpClient As TcpClient = DirectCast(client, TcpClient)
        Dim clientStream As NetworkStream = tcpClient.GetStream()
        Dim message As Byte() = New Byte(4096 * 12) {}
        Dim bytesRead As Integer
        While True
            bytesRead = 0
            bytesRead = clientStream.Read(message, 0, 4096 * 12)
            If bytesRead > 0 Then
                writeStream.Write(message, 0, bytesRead)
            Else
                Exit While
            End If
        End While
        writeStream.Close()
        tcpClient.Close()
        mCallingInstance.runRasterHeadless()
    End Sub

End Class
