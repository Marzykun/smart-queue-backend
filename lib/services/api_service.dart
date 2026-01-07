import 'dart:convert';
import 'package:http/http.dart' as http;

class ApiService {
  static const baseUrl = "https://smart-queue-backend-eu4z.onrender.com";


  Future<Map<String, dynamic>> getQueue() async {
    final url = Uri.parse("$baseUrl/shops/1/queue");
    final res = await http.get(url);

    if (res.statusCode != 200) {
      throw Exception("Failed to load queue");
    }

    return jsonDecode(res.body);
  }

  Future<void> addCustomer(String name, String phone) async {
    final url = Uri.parse("$baseUrl/shops/1/customers");

    await http.post(
      url,
      headers: {"Content-Type": "application/json"},
      body: jsonEncode({"name": name, "phone": phone}),
    );
  }

  Future<void> finish(int id) async {
  final url = Uri.parse("$baseUrl/queue/$id/finish");
  print("➡️ Calling finish endpoint: $url");
  final res = await http.post(url);
  print("⬅️ Response status: ${res.statusCode}");
  print("⬅️ Response body: ${res.body}");
}


  Future<void> arrived(int id) async {
    final url = Uri.parse("$baseUrl/queue/$id/arrived");
    await http.post(url);
  }

  Future<void> noShow(int id) async {
    final url = Uri.parse("$baseUrl/queue/$id/noshow");
    await http.post(url);
  }
}
