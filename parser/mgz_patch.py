"""Apply compatibility patches to mgz for AoE2:DE save versions >= 67.0 / 68.x (build 101.103+)."""

import struct
import io
import re
import mgz.fast.header as h
import mgz.fast.actions as a
from mgz.util import Version


_PATCHED = False

def apply_mgz_patches():
    global _PATCHED
    if _PATCHED:
        return
    _PATCHED = True

    # 1. Patch parse_metadata
    orig_parse_metadata = h.parse_metadata
    def patched_parse_metadata(header, save, skip_ai=True):
        if save >= 67.2:
            header.read(8)
        return orig_parse_metadata(header, save, skip_ai)

    h.parse_metadata = patched_parse_metadata

    # 2. Patch parse_de
    def patched_parse_de(data, version, save, skip=False):
        if version is not Version.DE:
            return None
        build = None
        if save >= 25.22 and not skip:
            build = h.unpack('<I', data)
        timestamp = None
        if save >= 26.16 and not skip:
            timestamp = h.unpack('<I', data)
        data.read(12)
        dlc_ids = []
        for i in range(0, h.unpack('<I', data)):
            dlc_ids.append(h.unpack('<I', data))
        data.read(4)
        if save >= 61.5:
            map_dimension = h.unpack('<I', data)
        else:
            difficulty_id = h.unpack('<I', data)
        data.read(4)
        rms_map_id = h.unpack('<I', data)
        data.read(4)
        victory_type_id = h.unpack('<I', data)
        starting_resources_id = h.unpack('<I', data)
        starting_age_id = h.unpack('<I', data)
        ending_age_id = h.unpack('<I', data)
        data.read(12)
        speed = h.unpack('<f', data)
        treaty_length = h.unpack('<I', data)
        population_limit = h.unpack('<I', data)
        num_players = h.unpack('<I', data)
        data.read(14)
        if save >= 61.5:
            difficulty_id = h.unpack('<B', data)
        random_positions, all_technologies = h.unpack('<bb', data)
        data.read(1)
        lock_teams = h.unpack('<b', data)
        lock_speed = h.unpack('<b', data)
        multiplayer = h.unpack('<b', data)
        cheats = h.unpack('<b', data)
        record_game = h.unpack('<b', data)
        animals_enabled = h.unpack('<b', data)
        predators_enabled = h.unpack('<b', data)
        turbo_enabled = h.unpack('<b', data)
        shared_exploration = h.unpack('<b', data)
        team_positions = h.unpack('<b', data)
        data.read(12)
        if save >= 25.06:
            data.read(1)
        if save > 50:
            data.read(1)
        players = []
        for _ in range(num_players if 66.3 > save >= 37 else 8):
            data.read(4)
            color_id = h.unpack('<i', data)
            data.read(2)
            team_id = h.unpack('<b', data)
            data.read(9)
            civilization_id = h.unpack('<I', data)
            custom_civ_selection = None
            if save >= 61.5:
                custom_civ_count = h.unpack('<I', data)
                if save >= 63.0 and custom_civ_count > 0:
                    custom_civ_selection = []
                    for _ in range(custom_civ_count):
                        custom_civ_selection.append(h.unpack('<I', data))
            
            # Robust de_string synchronization: if pointer is slightly off due to custom civ draft fields
            cur = data.tell()
            raw = data.getvalue()
            magic_pos = raw.find(b'\x60\x0a', cur)
            if magic_pos != -1 and (magic_pos - cur) <= 64:
                data.seek(magic_pos)

            h.de_string(data)
            data.read(1)
            ai_name = h.de_string(data)
            if save >= 66.3:
                censored_name = h.de_string(data)
            name = h.de_string(data)
            type = h.unpack('<I', data)
            profile_id, number = h.unpack('<I4xi', data)
            if save < 25.22:
                data.read(8)
            prefer_random = h.unpack('b', data)
            data.read(1)
            if save >= 25.06:
                data.read(8)
            if save >= 64.3:
                data.read(4)
            if save >= 67.2:
                h.de_string(data)

            players.append(dict(
                number=number,
                color_id=color_id,
                team_id=team_id,
                ai_name=ai_name,
                name=name,
                censored_name=censored_name if save >= 66.3 else name,
                type=type,
                profile_id=profile_id,
                civilization_id=civilization_id,
                custom_civ_selection=custom_civ_selection,
                prefer_random=prefer_random == 1
            ))
        data.read(12)
        if 66.3 > save >= 37:
            for _ in range(8 - num_players):
                if save >= 61.5:
                    data.read(4)
                data.read(12)
                h.de_string(data)
                data.read(1)
                h.de_string(data)
                h.de_string(data)
                data.read(38)
                if save >= 64.3:
                    data.read(4)
                if save >= 67.2:
                    h.de_string(data)
        data.read(4)
        rated = h.unpack('b', data)
        allow_specs = h.unpack('b', data)
        visibility = h.unpack('<I', data)
        hidden_civs = h.unpack('b', data)
        data.read(1)
        spec_delay = h.unpack('<I', data)
        data.read(1)
        strings = h.string_block(data)
        data.read(8)
        for _ in range(20):
            strings += h.string_block(data)
        data.read(4)
        if save < 25.22:
            data.read(236)
        if save >= 25.22:
            data.seek(-4, 1)
            l = h.unpack('<I', data)
            data.read(l * 4)
        for _ in range(h.unpack('<Q', data)):
            data.read(4)
            h.de_string(data)
            data.read(4)
        if save >= 25.02:
            data.read(8)
        guid = data.read(16)
        lobby = h.de_string(data)
        if save >= 25.22:
            data.read(8)
        mod = h.de_string(data)
        data.read(33)
        if save >= 20.06:
            data.read(1)
        if save >= 20.16:
            data.read(8)
        if save >= 25.06:
            data.read(21)
        if save >= 25.22:
            data.read(4)
        if save >= 26.16:
            data.read(8)
        if save >= 37:
            data.read(3)
        if save > 50:
            data.read(8)
        if save >= 61.5:
            data.read(1)
        if save >= 63:
            data.read(5)
        if save >= 66.3:
            c = h.unpack('<I', data)
            data.read(12)
            data.read(c * 4)
        if not skip:
            h.de_string(data)
            data.read(8)
            if save >= 37:
                timestamp, x = h.unpack('<II', data)
        rms_mod_id = None
        rms_filename = None
        import uuid, hashlib
        for s in strings:
            if s[0] == 'SUBSCRIBEDMODS' and s[1] == 'RANDOM_MAPS':
                rms_mod_id = s[3].split('_')[0]
                rms_filename = s[2]
        return dict(
            players=players,
            guid=str(uuid.UUID(bytes=guid)),
            hash=hashlib.sha1(guid),
            lobby=lobby.decode('utf-8'),
            mod=mod.decode('utf-8'),
            difficulty_id=difficulty_id,
            victory_type_id=victory_type_id,
            starting_resources_id=starting_resources_id,
            starting_age_id=starting_age_id - 2 if starting_age_id > 0 else 0,
            ending_age_id=ending_age_id - 2 if ending_age_id > 0 else 0,
            speed=speed,
            population_limit=population_limit,
            treaty_length=treaty_length,
            team_together=not bool(random_positions),
            all_technologies=bool(all_technologies),
            lock_teams=bool(lock_teams),
            lock_speed=bool(lock_speed),
            multiplayer=bool(multiplayer),
            cheats=bool(cheats),
            record_game=bool(record_game),
            animals_enabled=bool(animals_enabled),
            predators_enabled=bool(predators_enabled),
            turbo_enabled=bool(turbo_enabled),
            shared_exploration=bool(shared_exploration),
            team_positions=bool(team_positions),
            build=build,
            timestamp=timestamp,
            spec_delay=spec_delay,
            rated=rated == 1,
            allow_specs=bool(allow_specs),
            hidden_civs=bool(hidden_civs),
            visibility_id=visibility,
            rms_mod_id=rms_mod_id,
            rms_map_id=rms_map_id,
            rms_filename=rms_filename,
            dlc_ids=dlc_ids
        )

    h.parse_de = patched_parse_de

    # 3. Patch parse_action_71094 for DE_QUEUE in mgz.fast.actions
    orig_parse_action = a.parse_action_71094
    def patched_parse_action_71094(action_type, player_id, raw):
        if action_type is h.Action.DE_QUEUE:
            data = io.BytesIO(raw)
            selected = struct.unpack_from('<h', raw)[0]
            if len(raw) == 16 + 4 * selected:
                header_fmt = '<h4xhhh4x'
            elif len(raw) == 12 + 4 * selected:
                header_fmt = '<h4xhhh'
            else:
                header_fmt = '<h4xhhh'
            selected, building_type, unit_id, amount = h.unpack(header_fmt, data)
            object_ids = list(h.unpack(f'<{selected}I', data, shorten=False))
            return action_type, dict(object_ids=object_ids, amount=amount, unit_id=unit_id, player_id=player_id)
        return orig_parse_action(action_type, player_id, raw)

    a.parse_action_71094 = patched_parse_action_71094
